from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from owlready2 import get_ontology, destroy_entity,sync_reasoner, AllDifferent
from backend.parser import LRMLToDDLParser
from backend.reasoner import run_reasoner
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ONTOLOGY_PATH = str(Path(__file__).resolve().parent.parent.parent / "ontologija.rdf")
onto = get_ontology(ONTOLOGY_PATH).load()

for individual in list(onto.individuals()):
    destroy_entity(individual)

class Entity(BaseModel):
    class_name: str
    name: str

class Fact(BaseModel):
    subject: str
    predicate: str
    object: str
    not_: bool = Field(default=False, alias="not")

class ReasoningRequest(BaseModel):
    facts: list[Fact]

#dobavljanje svih klasa iz ontologije
@app.get("/ontology/classes")
def get_classes():

    classes = []

    for cls in onto.classes():
        if not list(cls.subclasses()):
            classes.append({
                "name": cls.name,
                "iri": cls.iri
            })

    return classes

#dobavljanje individua iz ontologije
@app.get("/ontology/individuals")
def get_individuals():

    individuals = []
    for individual in onto.individuals():
        classes = list(individual.is_a)
        if classes:
            class_name = classes[0].name
        else:
            class_name = ""

        individuals.append({
            "name": individual.name,
            "class_name": class_name,
            "iri": individual.iri
        })
    return individuals


#kreiranje instance
@app.post("/ontology/individuals")
def create_individual(request: Entity):

    cls = onto[request.class_name]
    if cls is None:
        return {
            "success": False,
            "message": "Klasa ne postoji."
        }

    individual_name = request.name.strip().replace(" ", "_")
    if not individual_name:
        return {
            "success": False,
            "message": "Naziv entiteta ne moze biti prazan."
        }

    existing = onto[individual_name]

    if existing is not None:
        return 

    individual = cls(individual_name)
    same_class_individuals = [
        ind
        for ind in onto.individuals()
        if ind != individual and cls in ind.is_a
    ]

    if same_class_individuals:
        AllDifferent(
            [*same_class_individuals, individual],
            ontology=onto
       )
    onto.save(file=ONTOLOGY_PATH,format="rdfxml")
    with onto:
            sync_reasoner()
    
    return {
        "success": True,
        "message": "Entitet je kreiran.",
        "name": individual.name,
        "class": cls.name,
        "iri": individual.iri
    }

#brisanje individue
@app.delete("/ontology/individuals")
def delete_individual(request: Entity):

    individual_name = request.name.strip().replace(" ", "_")
    if not individual_name:
        return {
            "success": False,
            "message": "Naziv entiteta ne moze biti prazan."
        }

    existing = onto[individual_name]
    if existing is None:
        return {
            "success": False,
            "message": "Entitet ne postoji."
        }

    destroy_entity(existing)
    onto.save(file=ONTOLOGY_PATH,format="rdfxml")
    with onto:
            sync_reasoner()    

    return {
        "success": True,
        "message": "Entitet je obrisan.",
        "name": individual_name
    }

#dobavi moguce relacije za klasu odabrane instance i individue koje pripadaju klasi kodomena odabrane relacije
@app.get("/ontology/fact-options")
def get_fact_options(class_name: str):

    selected_class = onto[class_name]
    if selected_class is None:
        return {
            "success": False,
            "message": f"Klasa '{class_name}' ne postoji.",
            "properties": []
        }

    object_properties = []
    for prop in onto.object_properties():
        if not prop.domain:
            continue

        allowed = False
        for domain_class in prop.domain:
            try:
                if selected_class == domain_class:
                    allowed = True
                    break

                if issubclass(selected_class, domain_class):
                    allowed = True
                    break
            except TypeError:
                pass
        if not allowed:
            continue


        ranges = []
        for range_class in prop.range:
            if not hasattr(range_class, "name"):
                continue

            objects = []
            for individual in onto.individuals():
                for individual_class in individual.is_a:
                    try:
                        if (individual_class == range_class or issubclass(individual_class, range_class)):
                            objects.append({
                                "name": individual.name,
                                "iri": individual.iri,
                                "class_name": individual_class.name
                            })
                            break
                    except TypeError:
                        pass

            ranges.append({
                "name": range_class.name,
                "iri": range_class.iri,
                "objects": objects
            })

        object_properties.append({
            "name": prop.name,
            "iri": prop.iri,
            "ranges": ranges
        })

    data_properties = []
    for prop in onto.data_properties():
        if not prop.domain:
            continue

        allowed = False
        for domain_class in prop.domain:
            try:
                if selected_class == domain_class:
                    allowed = True
                    break

                if issubclass(selected_class, domain_class):
                    allowed = True
                    break
            except TypeError:
                pass
        if not allowed:
            continue

        datatypes = []
        for datatype in prop.range:
            if hasattr(datatype, "name"):
                datatype_name = datatype.name
            else:
                datatype_name = str(datatype)
            datatypes.append(datatype_name)

        data_properties.append({
            "name": prop.name,
            "iri": prop.iri,
            "type": "data",
            "datatypes": datatypes
        })

    return {
        "success": True,
        "class_name": selected_class.name,
        "properties": object_properties,
        "data_properties": data_properties
    }


#rezonovanje na osnovu cinjenica i definisanih pravila 
@app.post("/reason")
def reason(request: ReasoningRequest):

    for individual in onto.individuals():
        for prop in onto.object_properties():
            values = getattr(individual, prop.name, [])
            if values:
                values.clear()
        for prop in onto.data_properties():
                    values = getattr(individual, prop.name, [])
                    if values:
                        values.clear()

    ddl_negative_facts = []
    for fact in request.facts:

        subject = onto[fact.subject]
        predicate = onto[fact.predicate]
        obj = onto[fact.object]

        if subject is None:
            return {
                "success": False,
                "message": f"Subjekat '{fact.subject}' ne postoji u ontologiji."
            }

        if predicate is None:
            return {
                "success": False,
                "message": f"Relacija '{fact.predicate}' ne postoji u ontologiji."
            }

        if obj is None:
            return {
                "success": False,
                "message": f"Objekat '{fact.object}' ne postoji u ontologiji."
            }

        if fact.not_ == False:
            predicate[subject].append(obj)
        else:
            predicate_name = fact.predicate

            negative_fact = (
                f"non({predicate_name}"
                f"({fact.subject.lower()},{fact.object.lower()}))"
            )

            positive_atom = (
                f"{predicate_name}"
                f"({fact.subject.lower()},{fact.object.lower()})"
            )

            ddl_negative_facts.append(
                f"fact({negative_fact})."
            )

            ddl_negative_facts.append(
                f"atom({negative_fact})."
            )

            ddl_negative_facts.append(
                f"atom({positive_atom})."
            )

    onto.save(file=ONTOLOGY_PATH,format="rdfxml")
    
    with onto:
        sync_reasoner()

    ddl_facts = ontology_to_ddl(onto)
    ddl_facts.extend(ddl_negative_facts)

    parser = LRMLToDDLParser(str(Path(__file__).resolve().parent.parent.parent / "zakon.xml"))

    ddl_rules = parser.parse()
    reasoner=run_reasoner(ddl_rules, ddl_facts)
    print("REZULTAT REASONERA:")
    print(reasoner)


    return {
        "success": True,
        "message": "Rezonovanje zavrseno.",
        "ontologija":reasoner
    }

def ontology_to_ddl(onto):
    ddl_facts = []

    def predicate_name(name):
        if not name:
            return name

        return name[0].lower() + name[1:]

    for individual in onto.individuals():
        for cls in individual.is_a:
            if hasattr(cls, "name"):
                predicate = predicate_name(cls.name)
                individual_name = individual.name.lower()

                fact = f"{predicate}({individual_name})"

                ddl_facts.append(f"fact({fact}).")
                ddl_facts.append(f"atom({fact}).")

    for individual in onto.individuals():
        for prop in onto.object_properties():
            values = getattr(individual, prop.name, [])

            for value in values:
                if hasattr(value, "name"):
                    predicate = predicate_name(prop.name)

                    subject = individual.name.lower()
                    obj = value.name.lower()

                    fact = (f"{predicate}("f"{subject},"f"{obj}"f")")

                    ddl_facts.append(f"fact({fact}).")
                    ddl_facts.append(f"atom({fact}).")

    return ddl_facts

