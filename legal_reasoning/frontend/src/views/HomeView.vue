<script setup>
import { ref } from 'vue'
import Relations from '@/components/Relations.vue'
import { useRouter } from 'vue-router'
import Entities from '@/components/Entities.vue'

const factsComponent = ref(null)
const relationsComponent = ref(null)
const router = useRouter()

async function loadFactsEntities() {
  await relationsComponent.value?.loadEntities()
}

function saveCurrentCase() {
  const entities =
    factsComponent.value?.getEntities() || []

  const facts =
    relationsComponent.value?.sendFacts() || []

  const caseState = {
    entities: JSON.parse(JSON.stringify(entities)),
    facts: JSON.parse(JSON.stringify(facts))
  }

  sessionStorage.setItem(
    'currentCase',
    JSON.stringify(caseState)
  )

  console.log('SAČUVAN CURRENT CASE:', caseState)
}

async function runReasoning() {
  const currentFacts =
    relationsComponent.value?.sendFacts() || []

  saveCurrentCase()

  console.log(
    'Šaljem činjenice na rezonovanje:',
    currentFacts
  )

  try {
    const response = await fetch(
      'http://localhost:8000/reason',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          facts: currentFacts
        })
      }
    )

    const result = await response.json()

    console.log(
      'Rezultat rezonovanja:',
      result
    )

    sessionStorage.setItem(
      'reasoningResult',
      JSON.stringify(result)
    )

    router.push('/reasoning-result')
  } catch (error) {
    console.error(
      'Greška prilikom rezonovanja:',
      error
    )
  }
}
</script>

<template>
  <main class="home-page">
    <div class="home-content">
      <h1 class="page-title"> Primena Zakona o zaštiti potrošača </h1>
      <Entities
        ref="factsComponent"
        @entities-changed="loadFactsEntities"
      />

      <Relations
        ref="relationsComponent"
      />

      <button
        type="button"
        class="reason-button"
        @click="runReasoning"
      >
        Rezonuj
      </button>
    </div>
  </main>
</template>

<style scoped>
.home-page {
  width: 100%;
  min-height: 100vh;
  background: white;
}

.home-content {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 30px 20px 50px;
  box-sizing: border-box;
}

.page-title { 
    margin: 0 0 35px; 
    text-align: center; 
    font-size: 32px; 
    font-weight: 700; 
    color: #222; 
}

.reason-button {
  display: block;
  margin: 30px auto;
  padding: 12px 30px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  background-color: #333;
  color: white;
}

.reason-button:hover {
  opacity: 0.85;
}
</style>