from lxml import etree
import re


LRML_NS = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"
RULEML_NS = "http://ruleml.org/spec"


class LRMLToDDLParser:

    def __init__(self, xml_path):
        self.xml_path = xml_path
        self.tree = etree.parse(xml_path)
        self.root = self.tree.getroot()

        self.rules = {}
        self.overrides = []

    def parse(self):
        self._parse_rules()
        self._parse_penalties()
        self._parse_reparations()
        self._parse_overrides()

        ddl = []

        for rule_id, rule in self.rules.items():
            ddl.append(self._rule_to_ddl(rule))

        ddl.extend(self._penalties_to_ddl())
        ddl.extend(self._overrides_to_ddl())

        return "\n".join(ddl)
    
    def _parse_rules(self):

        for ps in self.root.xpath(".//*[local-name()='PrescriptiveStatement']"):
            ps_key = ps.get("key")

            if not ps_key:
                continue

            rules = ps.xpath(".//*[local-name()='Rule']")

            if not rules:
                continue

            rule = rules[0]

            rule_key = rule.get("key")

            if not rule_key:
                rule_key = ps_key

            conditions = []
            conclusion = None

            obligation = rule.xpath(".//*[local-name()='Obligation']")
            prohibition = rule.xpath(".//*[local-name()='Prohibition']")

            if obligation:
                conclusion = self._extract_deontic_content(obligation[0])
            elif prohibition:
                conclusion = self._extract_deontic_content(prohibition[0],modality="pro")           

            if conclusion is None:
                conclusions = rule.xpath(".//*[local-name()='Conclusion']")

                if conclusions:
                    atoms = conclusions[0].xpath(".//*[local-name()='Atom']")

                    if atoms:
                        conclusion = self._extract_atom(atoms[0])

            if conclusion is None:
                continue

            ifs = rule.xpath(".//*[local-name()='if']")

            if ifs:
                and_elements = ifs[0].xpath("./*[local-name()='And']")

                if and_elements:
                    for element in and_elements[0]:
                        print("DEBUG element:", repr(element))
                        print("DEBUG type:", type(element))
                        if not isinstance(element, etree._Element):
                            continue

                        tag = etree.QName(element).localname

                        if tag not in ("Atom", "Negation"):
                            continue

                        text = self._extract_literal(element)

                        if text:
                            conditions.append(text)

            self.rules[rule_key] = {
                "rule_key": rule_key,
                "ps_key": ps_key,
                "conditions": conditions,
                "conclusion": conclusion
            }


    def _parse_overrides(self):

        for override in self.root.xpath(".//*[local-name()='Override']"):

            under = override.get("under")
            over = override.get("over")

            if not under or not over:
                continue

            under = under.lstrip("#")
            over = over.lstrip("#")

            self.overrides.append({
                "stronger": over,
                "weaker": under
            })


    def _rule_to_ddl(self, rule):
        rule_key = rule["rule_key"]
        conditions = rule["conditions"]
        conclusion = rule["conclusion"]

        ddl = []


        if conditions:
            condition_body = ",\n    ".join(
                f"fact({condition})"
                for condition in conditions
            )

            ddl.append(
                f"prescriptiveRule("
                f"{rule_key},"
                f"{conclusion}"
                f") :-\n"
                f"    {condition_body}."
            )

        else:
            ddl.append(f"prescriptiveRule({rule_key},{conclusion}).")

        for condition in conditions:

            if conditions:
                condition_body = ",\n    ".join(
                    f"fact({c})"
                    for c in conditions
                )

                ddl.append(
                    f"body({rule_key},{condition}) :-\n"
                    f"    {condition_body}."
                )

        return "\n".join(ddl)


    def _overrides_to_ddl(self):

        ddl = []

        for override in self.overrides:
            stronger = self._normalize_identifier(override["stronger"])

            weaker = self._normalize_identifier(override["weaker"])

            if not stronger or not weaker:
                continue

            ddl.append(f"superior({stronger},{weaker}).")

        return ddl
  
    def _extract_atom(self, atom):

        rel = atom.find("./{*}Rel")

        if rel is None:
            return None

        predicate = (rel.get("iri") or rel.get("key") or (rel.text or "")).strip()

        predicate = self._local_name(predicate)
        if predicate:
            predicate = predicate[0].lower() + predicate[1:]

        arguments = []

        for child in atom:
            tag = etree.QName(child).localname

            if tag == "Var":
                value = (child.text or "").strip()

                if value:
                    arguments.append(value)

            elif tag == "Ind":
                value = (child.get("iri") or (child.text or "")).strip()

                if value:
                    value = self._local_name(value)
                    value = value.lower()
                    arguments.append(value)


        if arguments:
            return f"{predicate}({','.join(arguments)})"

        return predicate


    def _extract_deontic_content(self, element, modality="obl"):

        for child in element:
            if not isinstance(child.tag, str):
                continue

            tag = etree.QName(child).localname

            if tag == "Atom":
                literal = self._extract_literal(child)

                if literal:
                    return f"{modality}({literal})"

            if tag == "Negation":
                literal = self._extract_literal(child)

                if literal:
                    return f"{modality}({literal})"

        text = "".join(element.itertext()).strip()

        return text or None
    
    @staticmethod
    def _local_name(value):
        if "#" in value:
            return value.rsplit("#", 1)[1]

        if "/" in value:
            return value.rsplit("/", 1)[1]

        return value

    @staticmethod
    def _normalize_identifier(value):

        if value is None:
            return ""

        value = value.strip()

        value = value.lstrip("#")

        value = re.sub(r"[^A-Za-z0-9_,()\-]","",value)

        return value

    def _parse_penalties(self):
        self.penalties = {}

        for penalty in self.root.findall(".//lrml:PenaltyStatement",{"lrml": LRML_NS}):
            penalty_key = penalty.get("key")

            if not penalty_key:
                continue

            obligation = penalty.find(".//lrml:Obligation",{"lrml": LRML_NS})

            if obligation is None:
                continue

            atom = obligation.find(".//ruleml:Atom",{"lrml": LRML_NS,"ruleml": "http://ruleml.org/spec"})

            if atom is None:
                continue

            conclusion = self._extract_atom(atom)

            min_amount = None
            max_amount = None
            amount = None

            for slot in atom.findall("./ruleml:slot",{"ruleml": "http://ruleml.org/spec"}):
                ind = slot.find("./ruleml:Ind",{"ruleml": "http://ruleml.org/spec"})

                if ind is None:
                    continue

                iri = ind.get("iri", "")
                value = (ind.text or "").strip()

                if not value:
                    continue

                try:
                    value = int(value)
                except ValueError:
                    continue

                if iri.endswith("#minKazna"):
                    min_amount = value

                elif iri.endswith("#maxKazna"):
                    max_amount = value

                elif iri.endswith("#amount"):
                    amount = value

            self.penalties[penalty_key] = {
                "penalty_key": penalty_key,
                "obligation_key": obligation.get("key"),
                "conclusion": conclusion,
                "amount": amount,
                "min": min_amount,
                "max": max_amount
            }

    def _parse_reparations(self):
    
        self.reparations = []

        for reparation in self.root.findall(".//lrml:Reparation",{"lrml": LRML_NS}):
            applies_penalty = reparation.find("lrml:appliesPenalty",{"lrml": LRML_NS})

            to_prescriptive = reparation.find("lrml:toPrescriptiveStatement",{"lrml": LRML_NS})

            if applies_penalty is None or to_prescriptive is None:
                continue

            penalty_key = applies_penalty.get("keyref")
            prescriptive_key = to_prescriptive.get("keyref")

            if not penalty_key or not prescriptive_key:
                continue

            penalty_key = penalty_key.lstrip("#")
            prescriptive_key = prescriptive_key.lstrip("#")

            self.reparations.append({
                "prescriptive_statement": prescriptive_key,
                "penalty": penalty_key
            })

    def _penalties_to_ddl(self):
        ddl = []

        for reparation in self.reparations:
            prescriptive_statement = reparation["prescriptive_statement"]

            penalty_key = reparation["penalty"]

            ddl.append(
                f"reparation("
                f"{prescriptive_statement},"
                f"{penalty_key}"
                f")."
            )

        return ddl

    def _extract_literal(self, element):
        tag = etree.QName(element).localname

        if tag == "Atom":
            return self._extract_atom(element)

        if tag == "Negation":
            atom = element.find("./{*}Atom")

            if atom is None:
                return None

            atom_text = self._extract_atom(atom)

            if atom_text is None:
                return None

            return f"non({atom_text})"
        return None
