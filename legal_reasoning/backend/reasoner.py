import re
from pathlib import Path
import clingo
import xml.etree.ElementTree as ET

ENGINE_FILES = [
    "asp/language.asp",
    "asp/basic_language.asp",
    "asp/deontic_language.asp",
    "asp/defeasible-ab.asp",
    "asp/deontic-comp.asp"
]

#ucitava zakon.txt i pravi recnik, gde je kljuc id zakona(rbr clana i stava)
def load_legal_text(path):
    
    legal_text = {}

    current_id = None
    current_text = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line.startswith("ID:"):
                if current_id and current_text:
                    legal_text[current_id] = current_text

                current_id = line.split(":", 1)[1].strip()
                current_text = None

            elif line.startswith("TEKST:"):
                current_text = line.split(":", 1)[1].strip()

        if current_id and current_text:
            legal_text[current_id] = current_text

    return legal_text

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LEGAL_TEXT_PATH = str( BASE_DIR / "zakon.txt")
legal_texts = load_legal_text(LEGAL_TEXT_PATH)
LEGAL_XML_PATH = str(BASE_DIR / "zakon.xml")

LEGAL_XML_ROOT = ET.parse(LEGAL_XML_PATH).getroot()

def run_reasoner(ddl_rules, ddl_facts):
    """
        pokrece rezonovanje i na osnovu rezultata poziva f-je za njihovu preradu
    """

    ctl = clingo.Control(["0","--warn=no-atom-undefined"])

    for file in ENGINE_FILES:
        ctl.load(file)

    print("========== DDL RULES ==========")
    print(ddl_rules)

    ddl_facts = "\n".join(ddl_facts)
    print("========== DDL FACTS ==========")
    print(ddl_facts)

    ctl.add("base", [], ddl_facts)
    ddl_bridges = """
    opposes(obl(X), obl(Y)) :-
        deonticRule(S, obl(Y)),
        deonticRule(T, obl(X)),
        applicable(S, obl(Y)),
        applicable(T, obl(X)),
        opposes(X, Y).
    """

    ddl_rules = ddl_rules + "\n" + ddl_bridges
    ctl.add("base", [], ddl_rules)
    ctl.ground([("base", [])])

    results = []
    violations = []
    conclusion = None

    for model in ctl.solve(yield_=True):
        symbols = model.symbols(shown=True)

        results.append([
            str(symbol)
            for symbol in symbols
        ])

        violated_rules = [
            symbol
            for symbol in symbols
            if symbol.name == "violatedRule"
        ]

        model_penalties = []

        for violation in violated_rules:
            if not violation.arguments:
                continue

            rule = str(violation.arguments[0])
            penalty = penaltyRegulation(rule)

            print("prekrseno:", rule)
            print("kazna:", penalty)

            if not penalty or not penalty.get("success"):
                continue

            model_penalties.append(penalty)

            violations.append({
                "rule": rule,
                "penalty": penalty
            })

        conclusion = determine_conclusion_and_steps(symbols,model_penalties)

        print("zakljucak")
        print(conclusion)

    unique_violations = []
    seen_violations = set()

    for violation in violations:
        rule = violation.get("rule")
        penalty = violation.get("penalty") or {}
        penalty_id = penalty.get("penalty")

        key = (rule, penalty_id)

        if key in seen_violations:
            continue

        seen_violations.add(key)
        unique_violations.append(violation)

    violations = unique_violations
    return {
        "results": results,
        "violations": violations,
        "conclusion":conclusion
    }


LRML_NS = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"


def penaltyRegulation(violated_rule):
    """
        na osnovu prekrsenog pravila vraca odgovarajuce kazne
    """
    
    root = LEGAL_XML_ROOT

    if "(" in violated_rule:
        rule_key = violated_rule.split("(", 1)[0]
    else:
        rule_key = violated_rule

    prescriptive_key = None

    for statement in root.findall(
        ".//lrml:PrescriptiveStatement",
        {"lrml": LRML_NS}
    ):
        rule = statement.find(
            "ruleml:Rule",
            {
                "lrml": LRML_NS,
                "ruleml": "http://ruleml.org/spec"
            }
        )

        if rule is not None and rule.get("key") == rule_key:
            prescriptive_key = statement.get("key")
            break

    if prescriptive_key is None:
        return {
            "success": False,
            "message":
                f"Nije pronađena preskriptivna norma "
                f"za pravilo {rule_key}."
        }

    penalty_key = None

    for reparation in root.findall(
        ".//lrml:Reparation",
        {"lrml": LRML_NS}
    ):
        to_prescriptive = reparation.find(
            "lrml:toPrescriptiveStatement",
            {"lrml": LRML_NS}
        )

        if to_prescriptive is None:
            continue

        keyref = to_prescriptive.get("keyref")

        if keyref == f"#{prescriptive_key}":
            applies_penalty = reparation.find(
                "lrml:appliesPenalty",
                {"lrml": LRML_NS}
            )

            if applies_penalty is not None:
                penalty_key = applies_penalty.get("keyref","").lstrip("#")

            break

    if penalty_key is None:
        return {
            "success": False,
            "message": (
                f"Za {prescriptive_key} nije pronađena "
                f"Reparation/Penalty veza."
            )
        }

    penalty_statement = root.find(
        f".//lrml:PenaltyStatement"
        f"[@key='{penalty_key}']",
        {"lrml": LRML_NS}
    )

    if penalty_statement is None:
        return {
            "success": False,
            "message":
                f"Nije pronađen PenaltyStatement {penalty_key}."
        }

    amount = None
    min_amount = None
    max_amount = None

    for ind in penalty_statement.findall(
        ".//ruleml:Ind",
        {
            "lrml": LRML_NS,
            "ruleml": "http://ruleml.org/spec"
        }
    ):
        iri = ind.get("iri")
        value = ind.text.strip() if ind.text else None

        if not value:
            continue

        try:
            value = int(value)
        except ValueError:
            continue

        if iri == "http://example.org/legal#amount":
            amount = value

        elif iri == "http://example.org/legal#minKazna":
            min_amount = value

        elif iri == "http://example.org/legal#maxKazna":
            max_amount = value

    return {
        "success": True,
        "rule": rule_key,
        "prescriptive_statement": prescriptive_key,
        "penalty": penalty_key,
        "amount": amount,
        "min": min_amount,
        "max": max_amount
    }

def determine_conclusion_and_steps(symbols, penalties=None):
    """
    Priprema korake pravnog rezonovanja za korisnički prikaz.
    """

    atoms = [str(symbol) for symbol in symbols]
    steps = []
    penalties = penalties or []

    # =========================================================
    # POMOCNE FUNKCIJE
    # =========================================================

    def starts_with(atom, predicate):
        return atom.startswith(predicate + "(")

    def get_atoms(predicate):
        return [
            atom
            for atom in atoms
            if starts_with(atom, predicate)
        ]

    def get_arguments(atom):
        start = atom.find("(")
        end = atom.rfind(")")

        if start == -1 or end == -1:
            return []

        content = atom[start + 1:end]

        result = []
        current = ""
        depth = 0

        for char in content:
            if char == "(":
                depth += 1

            elif char == ")":
                depth -= 1

            if char == "," and depth == 0:
                result.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            result.append(current.strip())

        return result

    def unwrap_obligation(literal):
        if (literal.startswith("obl(")and literal.endswith(")")):
            return literal[4:-1]

        return literal

    def format_rule(rule):
        match = re.match(r"^rule_clan(\d+)(?:_stav(\d+))?$",rule)

        if match:
            clan = match.group(1)
            stav = match.group(2)

            if stav:
                return f"Član {clan} stav {stav}"

            return f"Član {clan}"

        return rule

    def format_predicate(predicate):
        return re.sub(r"([a-z])([A-Z])",r"\1 \2",predicate).lower()

    def format_entity(entity):
        if not entity:
            return entity

        return entity[0].upper() + entity[1:]

    def format_literal(literal):
        literal = literal.strip()

        if (literal.startswith("non(") and literal.endswith(")")):
            literal = literal[4:-1]

        match = re.match(r"^([A-Za-z0-9_]+)\((.*)\)$",literal)

        if not match:
            return literal

        predicate = match.group(1)
        arguments = get_arguments(literal)

        predicate_text = format_predicate(predicate)

        if len(arguments) == 2:
            return (
                f"{format_entity(arguments[0])} "
                f"{predicate_text} "
                f"{format_entity(arguments[1])}"
            )

        if len(arguments) == 1:
            return (
                f"{predicate_text} "
                f"{format_entity(arguments[0])}"
            )

        return (
            f"{predicate_text} "
            f"{', '.join(format_entity(a) for a in arguments)}"
        )

    def format_normative_conclusion(rule_conclusion):

        if rule_conclusion.startswith("obl(non("):
            literal = rule_conclusion[4:-1]
            literal = literal[4:-1]

            return (
                f"Zabranjeno je da "
                f"{format_literal(literal)}."
            )

        if rule_conclusion.startswith("obl("):
            literal = rule_conclusion[4:-1]

            return (
                f"Obavezno je da "
                f"{format_literal(literal)}."
            )

        if rule_conclusion.startswith("perm("):
            literal = rule_conclusion[5:-1]

            return (
                f"Dozvoljeno je da "
                f"{format_literal(literal)}."
            )

        return rule_conclusion

    def add_prohibition_violation_step(rule,literal,fact):
        for step in steps:
            if (step.get("type") == "PROHIBITION_VIOLATION" and step.get("_rule") == rule):
                return

        steps.append({
            "level": 3,
            "type": "PROHIBITION_VIOLATION",
            "description":
                "Utvrđena činjenica predstavlja izvršenje "
                "radnje koja je zabranjena.",
            "fact": format_literal(fact),
            "literal": literal,
            "_rule": rule
        })

    def add_obligation_violation_step( rule,literal,fact):
        for step in steps:
            if (step.get("type") == "OBLIGATION_VIOLATION" and step.get("_rule") == rule):
                return

        steps.append({
            "level": 3,
            "type": "OBLIGATION_VIOLATION",
            "description":
                "Utvrđeno je da pozitivna obaveza nije ispunjena.",
            "fact": format_literal(fact),
            "literal": literal,
            "_rule": rule
        })

    def rule_to_legal_id(rule):
        if rule.startswith("rule_"):
            return rule[len("rule_"):]

        return rule

    # =========================================================
    # 1. PRIMENLJIVA PRAVILA
    # =========================================================

    applicable_rule_ids = set()

    for atom in get_atoms("applicable"):
        args = get_arguments(atom)

        if len(args) < 1:
            continue

        rule = args[0]
        applicable_rule_ids.add(rule)

    for rule in sorted(applicable_rule_ids):
        legal_id = rule_to_legal_id(rule)

        steps.append({
            "level": 1,
            "type": "RULE_APPLICABLE",
            "rule": format_rule(rule),
            "description": legal_texts.get(legal_id)
        })

    # =========================================================
    # 2. NORMATIVNE POZICIJE
    # =========================================================

    normative_positions = []

    obligation_atoms = get_atoms("obligation")

    for atom in obligation_atoms:

        args = get_arguments(atom)
        if len(args) < 2:
            continue

        rule = args[0]
        norm = args[1]

        literal = unwrap_obligation(norm)

        if literal.startswith("non("):

            normative_positions.append({
                "type": "PROHIBITION",
                "literal": literal,
                "rule": rule
            })

        else:

            normative_positions.append({
                "type": "OBLIGATION",
                "literal": literal,
                "rule": rule
            })

    # =========================================================
    # 3. SUKOBI
    # =========================================================

    seen_conflicts = set()

    for atom in get_atoms("obligationAttacking"):

        args = get_arguments(atom)

        if len(args) < 3:
            continue

        attacking_rule = args[0]
        attacking_literal = args[1]
        opposite_literal = args[2]

        if attacking_rule not in applicable_rule_ids:
            continue

        opposite_rule = None

        for obligation_atom in obligation_atoms:

            obligation_args = get_arguments(obligation_atom)

            if len(obligation_args) < 2:
                continue

            candidate_rule = obligation_args[0]
            candidate_literal = obligation_args[1]

            if (
                candidate_rule != attacking_rule
                and candidate_rule in applicable_rule_ids
                and candidate_literal == opposite_literal
            ):
                opposite_rule = candidate_rule
                break

        if opposite_rule is None:
            continue

        conflict_key = tuple(
            sorted([attacking_rule,
                    opposite_rule]))

        if conflict_key in seen_conflicts:
            continue

        seen_conflicts.add(conflict_key)

        steps.append({
            "level": 2,
            "type": "CONFLICT",
            "rule": format_rule(attacking_rule),
            "opposite_rule": format_rule(opposite_rule),
            "description":
                f"Pravilo {format_rule(attacking_rule)} "
                f"je u sukobu sa pravilom "
                f"{format_rule(opposite_rule)}.",
            "literal":
                format_normative_conclusion(
                    attacking_literal
                ),
            "opposite":
                format_normative_conclusion(
                    opposite_literal
                )
        })

    # =========================================================
    # 4. PRIORITETI
    # =========================================================

    superior = get_atoms("superior")

    seen_priorities = set()

    for atom in superior:

        args = get_arguments(atom)

        if len(args) < 2:
            continue

        stronger = args[0]
        weaker = args[1]

        if (stronger in applicable_rule_ids and weaker in applicable_rule_ids):

            priority_key = (stronger,weaker)

            if priority_key in seen_priorities:
                continue

            seen_priorities.add(priority_key)

            steps.append({
                "level": 2,
                "type": "PRIORITY",
                "description":
                    f"Pravilo {format_rule(stronger)} "
                    f"ima viši prioritet od pravila "
                    f"{format_rule(weaker)}.",
                "stronger_rule":
                    format_rule(stronger),
                "weaker_rule":
                    format_rule(weaker)
            })

    # =========================================================
    # 5. PORAZENA PRAVILA
    # =========================================================

    defeated_rules = set()
    seen_defeats = set()

    for atom in get_atoms("obligationDefeated"):

        args = get_arguments(atom)

        if not args:
            continue

        defeated_rule = args[0]

        defeated_rules.add(defeated_rule)

        if defeated_rule in seen_defeats:
            continue

        seen_defeats.add(defeated_rule)

        defeated_by = None

        for superior_atom in superior:

            superior_args = get_arguments(superior_atom)

            if len(superior_args) < 2:
                continue

            stronger = superior_args[0]
            weaker = superior_args[1]

            if (weaker == defeated_rule and stronger in applicable_rule_ids):
                defeated_by = stronger
                break

        step = {
            "level": 2,
            "type": "DEFEAT",
            "rule": format_rule(
                defeated_rule
            ),
            "description":
                f"Pravilo {format_rule(defeated_rule)} "
                f"je potisnuto zbog pravila "
                f"višeg prioriteta."
        }

        if defeated_by:
            step["defeated_by"] = format_rule(defeated_by)

        steps.append(step)

    # =========================================================
    # 6. AKTIVNE NORME
    # =========================================================

    active_norms = [
        norm
        for norm in normative_positions
        if norm["rule"] not in defeated_rules
    ]

    active_obligations = [
        norm
        for norm in active_norms
        if norm["type"] == "OBLIGATION"
    ]

    active_prohibitions = [
        norm
        for norm in active_norms
        if norm["type"] == "PROHIBITION"
    ]

    active_permissions = [
        norm
        for norm in active_norms
        if norm["type"] == "PERMISSION"
    ]

    # =========================================================
    # 7. CINJENICE
    # =========================================================

    fact_literals = set()

    for atom in get_atoms("fact"):

        args = get_arguments(atom)

        if args:
            fact_literals.add(args[0])

    # =========================================================
    # 8. ZABRANE
    # =========================================================

    prohibition_violation_found = False

    for norm in active_prohibitions:

        readable_result = (
            format_normative_conclusion(
                f"obl({norm['literal']})"))
        
        steps.append({
            "level": 2,
            "type": "ZABRANA",
            "result": readable_result
        })

        literal = norm["literal"]

        if not literal.startswith("non("):
            continue

        prohibited_literal = literal[4:-1]

        if prohibited_literal in fact_literals:

            add_prohibition_violation_step(norm["rule"],literal,prohibited_literal)
            prohibition_violation_found = True

    # =========================================================
    # 9. OBAVEZE
    # =========================================================

    obligation_violation_found = False

    for norm in active_obligations:

        readable_result = (
            format_normative_conclusion(f"obl({norm['literal']})"))

        steps.append({
            "level": 2,
            "type": "OBAVEZA",
            "result": readable_result
        })

        literal = norm["literal"]

        negative_literal = (f"non({literal})")

        if negative_literal in fact_literals:

            add_obligation_violation_step(norm["rule"],literal,negative_literal)
            obligation_violation_found = True

    has_unresolved_norm_conflict = False

    for obligation in active_obligations:

        obligation_literal = (obligation["literal"])

        for prohibition in active_prohibitions:

            prohibition_literal = (prohibition["literal"])

            if not prohibition_literal.startswith("non("):
                continue

            prohibition_action = (prohibition_literal[4:-1])

            if (obligation_literal== prohibition_action):
                has_unresolved_norm_conflict = True


    for first in active_obligations:

        for second in active_obligations:

            if first is second:
                continue

            first_literal = first["literal"]
            second_literal = second["literal"]

            if (first_literal.startswith("non(") and first_literal[4:-1] == second_literal):
                has_unresolved_norm_conflict = True

    if has_unresolved_norm_conflict:

        steps.append({
            "level": 3,
            "type": "UNRESOLVED_CONFLICT",
            "description":
                "Postoje suprotstavljene aktivne normativne "
                "pozicije koje nisu razrešene pravilom prioriteta."
        })

    # =========================================================
    # 11. KAZNE
    # =========================================================

    added_penalties = set()

    for penalty in penalties:

        if not isinstance(penalty, dict):
            continue

        if not penalty.get("success"):
            continue

        penalty_rule = penalty.get("rule")

        if (penalty_rule and penalty_rule in defeated_rules):
            continue

        penalty_id = penalty.get("penalty")

        if (not penalty_id or penalty_id in added_penalties):
            continue

        added_penalties.add(penalty_id)

        penalty_article = None

        match = re.search(r"penalty_clan(\d+)",penalty_id,re.IGNORECASE)

        if match:
            penalty_article = (f"Član {match.group(1)}")

        amount = penalty.get("amount")
        minimum = penalty.get("min")
        maximum = penalty.get("max")

        penalty_step = {
            "level": 4,
            "type": "KAZNA",
            "description":
                "Za utvrđenu povredu propisana je kazna.",
            "penalty": penalty_id
        }

        if penalty_article:
            penalty_step["penalty_article"]=penalty_article

        if amount is not None:
            penalty_step["amount"]=amount

        else:
            if minimum is not None:
                penalty_step["min"]=minimum

            if maximum is not None:
                penalty_step["max"]=maximum

        steps.append(penalty_step)

    # =========================================================
    # 12. DOZVOLE
    # =========================================================

    for norm in active_permissions:

        readable_result = (format_normative_conclusion( norm["literal"]))

        steps.append({
            "level": 2,
            "type": "DOZVOLA",
            "result": readable_result
        })

    # =========================================================
    # 13. KONACAN ZAKLJUCAK
    # =========================================================
    if has_unresolved_norm_conflict:

        return {
            "conclusion": "SUKOB_NORMI",
            "steps": steps
        }

    if prohibition_violation_found:
        return {
            "conclusion": "POVREDA_ZABRANE",
            "steps": steps
        }

    if obligation_violation_found:
        return {
            "conclusion": "POVREDA_OBAVEZE",
            "steps": steps
        }

    if active_permissions:
        return {
            "conclusion": "DOZVOLA",
            "steps": steps
        }

    if active_prohibitions:
        return {
            "conclusion": "ZABRANA",
            "steps": steps
        }

    if active_obligations:
        return {
            "conclusion": "OBAVEZA",
            "steps": steps
        }

    steps.append({
        "level": 3,
        "type": "UNDETERMINED",
        "description":
            "Na osnovu dostupnih rezultata nije moguće "
            "formirati konačan pravni zaključak."
    })

    return {
        "conclusion": "NEODREĐENO",
        "steps": steps
    }