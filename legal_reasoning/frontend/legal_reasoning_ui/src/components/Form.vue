<script setup>
import { ref, onMounted } from 'vue'

const classes = ref([])

// Svi entiteti koje korisnik ima na ekranu
const entities = ref([])

onMounted(async () => {
    const response = await fetch(
        'http://localhost:8000/ontology/classes'
    )

    classes.value = await response.json()
})

// Dodavanje novog entiteta
function addEntity() {
    entities.value.push({
        id: Date.now(),
        className: '',
        name: '',
        saved: false
    })
}

// Kreiranje instance u OWL-u
async function createEntity(entity) {

    // Provera da li su uneti svi podaci
    if (!entity.className || !entity.name.trim()) {
        alert('Izaberite tip entiteta i unesite naziv.')
        return
    }

    try {

        const response = await fetch(
            'http://localhost:8000/ontology/individuals',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    class_name: entity.className,
                    name: entity.name
                })
            }
        )

        const result = await response.json()

        console.log(result)

        if (result.success) {

            // Označavamo da je entitet sačuvan
            entity.saved = true

        } else {

            alert(result.message)
        }

    } catch (error) {

        console.error(
            'Greška prilikom kreiranja instance:',
            error
        )

        alert('Greška prilikom povezivanja sa serverom.')
    }
}

// Brisanje entiteta
async function removeEntity(entity, index) {

    // Ako je entitet prethodno sačuvan,
    // obriši ga i iz OWL-a
    if (entity.saved) {

        try {

            const response = await fetch(
                'http://localhost:8000/ontology/individuals',
                {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        class_name: entity.className,
                        name: entity.name
                    })
                }
            )

            const result = await response.json()

            console.log(result)

            if (!result.success) {
                alert(result.message)
                return
            }

        } catch (error) {

            console.error(
                'Greška prilikom brisanja instance:',
                error
            )

            alert('Greška prilikom povezivanja sa serverom.')
            return
        }
    }

    // Ukloni entitet sa ekrana
    entities.value.splice(index, 1)
}
</script>


<template>

    <div class="knowledge-form">

        <!-- ==================== ENTITETI ==================== -->

        <section class="section">

            <h2>Entiteti</h2>

            <div class="entity-form">

                <div
                    v-for="(entity, index) in entities"
                    :key="entity.id"
                    class="form-row"
                >

                    <!-- Klasa -->

                    <div class="form-group">

                        <label>Klasa</label>

                        <select
                            v-model="entity.className"
                            :disabled="entity.saved"
                        >

                            <option value="">
                                Izaberi tip entiteta
                            </option>

                            <option
                                v-for="item in classes"
                                :key="item.iri"
                                :value="item.name"
                            >
                                {{ item.name }}
                            </option>

                        </select>

                    </div>


                    <!-- Dve tačke -->

                    <div class="colon">
                        :
                    </div>


                    <!-- Naziv -->

                    <div class="form-group instance-group">

                        <label>Naziv</label>

                        <input
                            v-model="entity.name"
                            type="text"
                            placeholder="Unesite naziv"
                            :disabled="entity.saved"
                        />

                    </div>


                    <!-- Sačuvaj -->

                    <button
                        v-if="!entity.saved"
                        type="button"
                        class="save-entity-button"
                        @click="createEntity(entity)"
                    >
                        Sačuvaj
                    </button>


                    <!-- X -->

                    <button
                        type="button"
                        class="remove-button"
                        @click="removeEntity(entity, index)"
                    >
                        ×
                    </button>

                </div>

            </div>


            <!-- Dodavanje novog entiteta -->

            <button
                type="button"
                class="add-button"
                @click="addEntity"
            >
                <span>+</span>
                Entitet
            </button>

        </section>


        <!-- ==================== ČINJENICE ==================== -->

        <section class="section facts-section">

            <h2>Činjenice</h2>

            <div class="fact-form">

                <div class="form-group">

                    <label>Entitet</label>

                    <select>

                        <option value="">
                            Odaberite entitet
                        </option>

                        <option value="petar">
                            Petar
                        </option>

                        <option value="ana">
                            Ana
                        </option>

                    </select>

                </div>


                <div class="form-group">

                    <label>Relacija</label>

                    <select>

                        <option value="">
                            Odaberite relaciju
                        </option>

                        <option value="worksFor">
                            radi_za
                        </option>

                        <option value="owns">
                            poseduje
                        </option>

                    </select>

                </div>


                <div class="form-group">

                    <label>Objekat</label>

                    <select>

                        <option value="">
                            Odaberite objekat
                        </option>

                        <option value="company">
                            Firma
                        </option>

                        <option value="organization">
                            Organizacija
                        </option>

                    </select>

                </div>

            </div>


            <!-- Dodavanje činjenice -->

            <button
                type="button"
                class="add-button"
            >
                <span>+</span>
                Činjenica
            </button>

        </section>

    </div>

</template>


<style scoped>

.remove-button {
    margin-top: 24px;
    width: 34px;
    height: 34px;
    border: none;
    border-radius: 50%;
    background: #e74c3c;
    color: white;
    font-size: 22px;
    font-weight: bold;
    cursor: pointer;
}

.remove-button:hover {
    background: #c0392b;
}


.save-entity-button {
    margin-top: 24px;
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    background: #3498db;
    color: white;
    font-size: 14px;
    cursor: pointer;
}

.save-entity-button:hover {
    background: #2980b9;
}


.remove-button,
.save-entity-button {
    flex-shrink: 0;
}


select:disabled,
input:disabled {
    background-color: #f1f1f1;
    cursor: not-allowed;
}

</style>