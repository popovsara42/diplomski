<script setup>
import { ref, onMounted } from 'vue'

onMounted(async () => {
    await loadEntities()
    await restoreCurrentCase()
})

const entities = ref([])
const facts = ref([
    {
        id: Date.now(),
        entity: '',
        property: '',
        object: '',
        not: false,
        properties: [],
        objects: [],
        data_properties: [],
        propertyType: '',
        dataType: ''
    }
])

async function loadEntities() {
    try {
        const response = await fetch(
            'http://localhost:8000/ontology/individuals'
        )

        const result = await response.json()
        entities.value = result
    } catch (error) {
        console.error(
            'Greška prilikom učitavanja individua:',
            error
        )
    }
}

async function restoreCurrentCase() {
    const savedCase = sessionStorage.getItem('currentCase')

    if (!savedCase) {
        return
    }

    try {
        const caseState = JSON.parse(savedCase)

        if (!caseState.facts?.length) {
            return
        }

        facts.value = caseState.facts.map(fact => ({
            id: Date.now() + Math.random(),
            entity: fact.subject,
            property: fact.predicate,
            object: fact.object,
            not: fact.not || false,
            properties: [],
            objects: [],
            data_properties: [],
            propertyType: '',
            dataType: ''
        }))

        for (const fact of facts.value) {
            await restoreFact(fact)
        }
    } catch (error) {
        console.error(
            'Greška prilikom učitavanja sačuvanog slučaja:',
            error
        )
    }
}

async function restoreFact(fact) {
    if (!fact.entity) {
        return
    }

    const entity = entities.value.find(
        item => item.name === fact.entity
    )

    if (!entity) {
        return
    }

    try {
        const response = await fetch(
            `http://localhost:8000/ontology/fact-options?class_name=${encodeURIComponent(entity.class_name)}`
        )

        const result = await response.json()

        if (!result.success) {
            return
        }

        fact.properties = result.properties || []
        fact.data_properties = result.data_properties || []

        const objectProperty = fact.properties.find(
            item => item.name === fact.property
        )

        if (objectProperty) {
            fact.propertyType = 'object'
            fact.objects = objectProperty.ranges.flatMap(
                range => range.objects || []
            )
            return
        }

        const dataProperty = fact.data_properties.find(
            item => item.name === fact.property
        )

        if (dataProperty) {
            fact.propertyType = 'data'
            fact.dataType =
                dataProperty.datatypes?.[0] || ''
        }
    } catch (error) {
        console.error(
            'Greška prilikom restauracije činjenice:',
            error
        )
    }
}


function resetFacts() {
    facts.value = [
        {
            id: Date.now(),
            entity: '',
            property: '',
            object: '',
            not: false,
            properties: [],
            objects: [],
            data_properties: [],
            propertyType: '',
            dataType: ''
        }
    ]
}

function addFact() {
    facts.value.push({
        id: Date.now() + Math.random(),
        entity: '',
        property: '',
        object: '',
        not: false,
        properties: [],
        objects: [],
        data_properties: [],
        propertyType: '',
        dataType: ''
    })
}

function removeFact(id) {
    facts.value = facts.value.filter(
        fact => fact.id !== id
    )

    if (facts.value.length === 0) {
        resetFacts()
    }
}

async function loadProperties(fact) {
    fact.property = ''
    fact.object = ''
    fact.properties = []
    fact.objects = []
    fact.data_properties = []
    fact.propertyType = ''
    fact.dataType = ''

    if (!fact.entity) {
        return
    }

    const entity = entities.value.find(
        item => item.name === fact.entity
    )

    if (!entity) {
        return
    }

    try {
        const response = await fetch(
            `http://localhost:8000/ontology/fact-options?class_name=${encodeURIComponent(entity.class_name)}`
        )

        const result = await response.json()

        if (result.success) {
            fact.properties = result.properties || []
            fact.data_properties = result.data_properties || []
        } else {
            fact.properties = []
            fact.data_properties = []
            alert(result.message)
        }
    } catch (error) {
        console.error(
            'Greška prilikom učitavanja relacija:',
            error
        )
        fact.properties = []
        fact.data_properties = []
    }
}

function loadObjects(fact) {
    fact.object = ''
    fact.objects = []
    fact.propertyType = ''
    fact.dataType = ''

    if (!fact.property) {
        return
    }

    const objectProperty = fact.properties.find(
        item => item.name === fact.property
    )

    if (objectProperty) {
        fact.propertyType = 'object'
        fact.objects = objectProperty.ranges.flatMap(
            range => range.objects || []
        )
        return
    }

    const dataProperty = fact.data_properties.find(
        item => item.name === fact.property
    )

    if (dataProperty) {
        fact.propertyType = 'data'
        fact.dataType =
            dataProperty.datatypes?.[0] || ''
    }
}

function sendFacts() {
    const validFacts = facts.value
        .filter(fact =>
            fact.entity &&
            fact.property &&
            fact.object !== ''
        )
        .map(fact => ({
            subject: fact.entity,
            predicate: fact.property,
            object: fact.object,
            not: fact.not
        }))

    console.log(
        'FACTS KOJE ŠALJEM:',
        validFacts
    )

    return validFacts
}

defineExpose({
    loadEntities,
    sendFacts,
    resetFacts
})
</script>

<template>
    <section class="section facts-section">
        <h2>Činjenice</h2>

        <div
            v-for="fact in facts"
            :key="fact.id"
            class="fact-form"
        >
            <div class="form-group">
                <label>Entitet</label>

                <select
                    v-model="fact.entity"
                    @change="loadProperties(fact)"
                >
                    <option value="">
                        Izaberi entitet
                    </option>

                    <option
                        v-for="item in entities"
                        :key="item.iri"
                        :value="item.name"
                    >
                        {{ item.name }}
                    </option>
                </select>
            </div>

            <div class="not-group">
                <label>NOT</label>

                <input
                    type="checkbox"
                    v-model="fact.not"
                    :disabled="!fact.entity"
                />
            </div>

            <div class="form-group">
                <label>Relacija</label>

                <select
                    v-model="fact.property"
                    :disabled="!fact.entity"
                    @change="loadObjects(fact)"
                >
                    <option value="">
                        Odaberite relaciju
                    </option>

                    <option
                        v-for="property in fact.properties"
                        :key="property.iri"
                        :value="property.name"
                    >
                        {{ property.name }}
                    </option>

                    <option
                        v-for="property in fact.data_properties"
                        :key="property.iri"
                        :value="property.name"
                    >
                        {{ property.name }}
                    </option>
                </select>
            </div>

            <div class="form-group">
                <label>
                    {{
                        fact.propertyType === 'data'
                            ? 'Vrednost'
                            : 'Objekat'
                    }}
                </label>

                <select
                    v-if="fact.propertyType === 'object'"
                    v-model="fact.object"
                >
                    <option value="">
                        Odaberite objekat
                    </option>

                    <option
                        v-for="object in fact.objects"
                        :key="object.iri"
                        :value="object.name"
                    >
                        {{ object.name }}
                    </option>
                </select>

                <input
                    v-else-if="
                        fact.propertyType === 'data' &&
                        fact.dataType === 'string'
                    "
                    type="text"
                    v-model="fact.object"
                    placeholder="Unesite vrednost"
                />

                <input
                    v-else-if="
                        fact.propertyType === 'data' &&
                        fact.dataType === 'integer'
                    "
                    type="number"
                    v-model="fact.object"
                    placeholder="Unesite broj"
                />

                <select
                    v-else-if="
                        fact.propertyType === 'data' &&
                        fact.dataType === `<class 'bool'>`
                    "
                    v-model="fact.object"
                >
                    <option value="">
                        Odaberite
                    </option>

                    <option value="true">
                        Yes
                    </option>

                    <option value="false">
                        No
                    </option>
                </select>

                <input
                    v-else
                    type="text"
                    disabled
                    placeholder="Prvo izaberite relaciju ili podatak"
                />
            </div>

            <button
                type="button"
                class="remove-fact-button"
                @click="removeFact(fact.id)"
                title="Obriši činjenicu"
            >
                ×
            </button>
        </div>

        <button
            type="button"
            class="add-button"
            @click="addFact"
        >
            <span>+</span>
            Činjenica
        </button>
    </section>
</template>

<style scoped>
.fact-form {
    display: flex;
    align-items: flex-end;
    gap: 15px;
    margin-bottom: 15px;
    padding: 15px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #fafafa;
}

.fact-form .form-group {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.fact-form .form-group label {
    margin-bottom: 7px;
    font-size: 14px;
    font-weight: 500;
    color: #374151;
}

.fact-form select,
.fact-form input[type="text"],
.fact-form input[type="number"] {
    height: 40px;
    padding: 8px 10px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: white;
    font-size: 14px;
    color: #141414;
}

.fact-form select:focus,
.fact-form input[type="text"]:focus,
.fact-form input[type="number"]:focus {
    outline: none;
    border-color: #9ca3af;
}

.not-group {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 40px;
    flex-shrink: 0;
    margin-bottom: 0;
}

.not-group label {
    margin-bottom: 10px;
    font-size: 14px;
    font-weight: 500;
    color: #374151;
}

.not-group input {
    width: 18px;
    height: 18px;
    margin-bottom: 10px;
    cursor: pointer;
}

.remove-fact-button {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    border: none;
    border-radius: 8px;
    background-color: #e53935;
    color: white;
    font-size: 26px;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}

.remove-fact-button:hover {
    opacity: 0.85;
}

.add-button {
    margin-top: 10px;
    cursor: pointer;
}
</style>