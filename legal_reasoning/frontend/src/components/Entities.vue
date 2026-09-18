<script setup>
import { ref, onMounted } from 'vue'

const classes = ref([])
const entities = ref([])

const emit = defineEmits(['entities-changed'])

onMounted(async () => {
  try {
    const classesResponse = await fetch(
      'http://localhost:8000/ontology/classes'
    )

    classes.value = await classesResponse.json()

    await loadEntities()
  } catch (error) {
    console.error(
      'Greška prilikom učitavanja podataka:',
      error
    )
  }
})

function createEmptyEntity() {
  return {
    id: Date.now() + Math.random(),
    className: '',
    name: '',
    saved: false
  }
}

async function loadEntities() {
  try {
    const response = await fetch(
      'http://localhost:8000/ontology/individuals'
    )

    const individuals = await response.json()
    const savedCase = sessionStorage.getItem('currentCase')

    if (savedCase) {
      const caseState = JSON.parse(savedCase)

      if (caseState.entities?.length) {
        entities.value = [
          ...caseState.entities,
          createEmptyEntity()
        ]
        return
      }
    }

    entities.value = individuals.map(individual => ({
      id: Date.now() + Math.random(),
      className: individual.class_name,
      name: individual.name,
      saved: true
    }))

    entities.value.push(createEmptyEntity())
  } catch (error) {
    console.error(
      'Greška prilikom učitavanja individua:',
      error
    )
  }
}

function getEntities() {
  return entities.value.filter(
    entity =>
      entity.saved &&
      entity.className &&
      entity.name.trim()
  )
}

function addEntity() {
  entities.value.push(createEmptyEntity())
}

async function createEntity(entity) {
  if (!entity.className || !entity.name.trim()) {
    alert(
      'Izaberite tip entiteta i unesite naziv.'
    )
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

    if (result.success) {
      entity.saved = true

      emit('entities-changed')
    } else {
      alert(result.message)
    }
  } catch (error) {
    console.error(
      'Greška prilikom kreiranja instance:',
      error
    )

    alert(
      'Greška prilikom povezivanja sa serverom.'
    )
  }
}


async function removeEntity(entity, index) {
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

      if (!result.success) {
        alert(result.message)
        return
      }
    } catch (error) {
      console.error(
        'Greška prilikom brisanja instance:',
        error
      )

      alert(
        'Greška prilikom povezivanja sa serverom.'
      )

      return
    }
  }

  entities.value.splice(index, 1)

  emit('entities-changed')
}

defineExpose({
  getEntities,
  loadEntities
})
</script>

<template>
  <div class="knowledge-form">
    <section class="section">
      <h2>Entiteti</h2>

      <div class="entity-form">
        <form
          v-for="(entity, index) in entities"
          :key="entity.id"
          class="entity-row"
          @submit.prevent="createEntity(entity)"
        >
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

          <div class="colon">
            :
          </div>

          <div class="form-group instance-group">
            <label>Naziv</label>

            <input
              v-model="entity.name"
              type="text"
              placeholder="Unesite naziv"
              :disabled="entity.saved"
            />
          </div>

          <button
            v-if="!entity.saved"
            type="submit"
            class="save-entity-button"
          >
            Sačuvaj
          </button>

          <button
            type="button"
            class="remove-button"
            @click="removeEntity(entity, index)"
            title="Obriši entitet"
          >
            ×
          </button>
        </form>
      </div>

      <button
        type="button"
        class="add-button"
        @click="addEntity"
      >
        <span>+</span>
        Entitet
      </button>
    </section>
  </div>
</template>

<style scoped>
.entity-row {
  display: flex;
  align-items: flex-end;
  gap: 15px;
  width: 100%;
  margin-bottom: 15px;
  padding: 15px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
}

.entity-row .form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.entity-row .form-group label {
  margin-bottom: 7px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.entity-row select,
.entity-row input {
  height: 40px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #141414;
  font-size: 14px;
}

.entity-row select:focus,
.entity-row input:focus {
  outline: none;
  border-color: #9ca3af;
}

.instance-group {
  flex: 1;
}

.colon {
  align-self: flex-end;
  margin-bottom: 8px;
  font-size: 22px;
  font-weight: bold;
  color: #374151;
  flex-shrink: 0;
}

.save-entity-button {
  height: 40px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #3498db;
  color: white;
  font-size: 14px;
  cursor: pointer;
  flex-shrink: 0;
}

.save-entity-button:hover {
  background: #2980b9;
}

.remove-button {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: #e74c3c;
  color: white;
  font-size: 22px;
  font-weight: bold;
  cursor: pointer;
  flex-shrink: 0;
}

.remove-button:hover {
  background: #c0392b;
}

select:disabled,
input:disabled {
  background-color: #f1f1f1;
  cursor: not-allowed;
}

.add-button {
  margin-top: 5px;
  cursor: pointer;
}
</style>