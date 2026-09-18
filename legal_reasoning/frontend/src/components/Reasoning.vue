<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const result = ref(null)

onMounted(() => {
  const savedResult = sessionStorage.getItem('reasoningResult')

  if (savedResult) {
    result.value = JSON.parse(savedResult)
  }
})

const steps = computed(() => {
  return (
    result.value
      ?.ontologija
      ?.conclusion
      ?.steps || []
  )
})

function formatStepType(type) {
  const types = {
    RULE_APPLICABLE: 'PRIMENLJIVO PRAVILO',
    ZABRANA: 'ZABRANA',
    OBAVEZA: 'OBAVEZA',
    DOZVOLA: 'DOZVOLA',
    PROHIBITION_VIOLATION: 'POVREDA ZABRANE',
    OBLIGATION_VIOLATION: 'POVREDA OBAVEZE',
    KAZNA: 'KAZNA',
    CONFLICT: 'SUKOB NORMI',
    PRIORITY: 'PRIORITET PRAVILA',
    DEFEAT: 'POTISKIVANJE PRAVILA'
  }

  return types[type] || type
}

function formatMoney(value) {
  return new Intl.NumberFormat('sr-RS').format(value)
}

function prosiriCinjenicama() {
  router.back()
}

async function novoRezonovanje() {
  try {
    const response = await fetch(
      'http://localhost:8000/ontology/individuals'
    )

    const individuals = await response.json()

    for (const individual of individuals) {
      const deleteResponse = await fetch(
        'http://localhost:8000/ontology/individuals',
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            class_name: individual.class_name,
            name: individual.name
          })
        }
      )

      const deleteResult = await deleteResponse.json()

      if (!deleteResult.success) {
        console.error(
          `Greška pri brisanju ${individual.name}:`,
          deleteResult.message
        )
      }
    }

    sessionStorage.removeItem('currentCase')
    sessionStorage.removeItem('reasoningResult')

    router.back()
  } catch (error) {
    console.error(
      'Greška prilikom brisanja svih individua:',
      error
    )
  }
}
</script>

<template>
  <div class="result-page">
    <!-- PORUKA -->
    <div v-if="result?.message" class="message">
      {{ result.message }}
    </div>

    <!-- KORACI REZONOVANJA -->
    <section class="steps-section">
      <h2>Koraci rezonovanja</h2>

      <div v-if="steps.length" class="steps">
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="step-card"
        >
          <div class="step-number">
            {{ index + 1 }}
          </div>

          <div class="step-content">
            <div class="step-type">
              {{ formatStepType(step.type) }}
            </div>

            <!-- PRIMENLJIVO PRAVILO -->
            <template v-if="step.type === 'RULE_APPLICABLE'">
              <h3>
                {{ step.rule }}
              </h3>

              <div v-if="step.description" class="detail">
                <span class="detail-label">
                  Pravilo:
                </span>

                <code>
                  {{ step.description }}
                </code>
              </div>
            </template>

            <!-- ZABRANA / OBAVEZA / DOZVOLA -->
            <template
              v-else-if="
                step.type === 'ZABRANA' ||
                step.type === 'OBAVEZA' ||
                step.type === 'DOZVOLA'
              "
            >
              <div v-if="step.result" class="detail">
                <span class="detail-label">
                  Normativna pozicija:
                </span>

                <code>
                  {{ step.result }}
                </code>
              </div>
            </template>

            <!-- POVREDA ZABRANE -->
            <template
              v-else-if="step.type === 'PROHIBITION_VIOLATION'"
            >
              <div v-if="step.fact" class="detail">
                <span class="detail-label">
                  Činjenica koja dovodi do povrede zabrane:
                </span>

                <code>
                  {{ step.fact }}
                </code>
              </div>
            </template>

            <!-- POVREDA OBAVEZE -->
            <template
              v-else-if="step.type === 'OBLIGATION_VIOLATION'"
            >
              <div v-if="step.fact" class="detail">
                <span class="detail-label">
                  Činjenica koja dovodi do povrede obaveze:
                </span>

                <code>
                  {{ step.fact }}
                </code>
              </div>

              <div v-if="step.description" class="detail">
                <span class="detail-label">
                  Zaključak:
                </span>

                <code>
                  {{ step.description }}
                </code>
              </div>
            </template>

            <!-- KAZNA -->
            <template v-else-if="step.type === 'KAZNA'">
              <div v-if="step.penalty_article" class="detail">
                <span class="detail-label">
                  Kazna za izvršen prekršaj određena je članom:
                </span>

                <code>
                  {{ step.penalty_article }}
                </code>
              </div>

              <div
                v-if="
                  step.amount !== null &&
                  step.amount !== undefined
                "
                class="detail"
              >
                <span class="detail-label">
                  Iznos kazne:
                </span>

                <code>
                  {{ formatMoney(step.amount) }} dinara
                </code>
              </div>

              <div
                v-else-if="
                  step.min !== null ||
                  step.max !== null
                "
                class="detail"
              >
                <span class="detail-label">
                  Raspon kazne:
                </span>

                <code>
                  <template v-if="step.min !== null">
                    najmanje {{ formatMoney(step.min) }} dinara
                  </template>

                  <template
                    v-if="
                      step.min !== null &&
                      step.max !== null
                    "
                  >
                    , 
                  </template>

                  <template v-if="step.max !== null">
                    najviše {{ formatMoney(step.max) }} dinara
                  </template>
                </code>
              </div>
            </template>

            <!-- SUKOB -->
            <template v-else-if="step.type === 'CONFLICT'">
              <div v-if="step.description" class="detail">
                <span class="detail-label">
                  Opis:
                </span>

                <code>
                  {{ step.description }}
                </code>
              </div>

              <div v-if="step.literal" class="detail">
                <span class="detail-label">
                  Norma:
                </span>

                <code>
                  {{ step.literal }}
                </code>
              </div>

              <div v-if="step.opposite" class="detail">
                <span class="detail-label">
                  Suprotna norma:
                </span>

                <code>
                  {{ step.opposite }}
                </code>
              </div>
            </template>

            <!-- PRIORITET -->
            <template v-else-if="step.type === 'PRIORITY'">
              <div v-if="step.description" class="detail">
                <span class="detail-label">
                  Opis:
                </span>

                <code>
                  {{ step.description }}
                </code>
              </div>

              <div v-if="step.stronger_rule" class="detail">
                <span class="detail-label">
                  Pravilo višeg prioriteta:
                </span>

                <code>
                  {{ step.stronger_rule }}
                </code>
              </div>

              <div v-if="step.weaker_rule" class="detail">
                <span class="detail-label">
                  Pravilo nižeg prioriteta:
                </span>

                <code>
                  {{ step.weaker_rule }}
                </code>
              </div>
            </template>

            <!-- POTISKIVANJE PRAVILA -->
            <template v-else-if="step.type === 'DEFEAT'">
              <div v-if="step.description" class="detail">
                <span class="detail-label">
                  Opis:
                </span>

                <code>
                  {{ step.description }}
                </code>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        Nema dostupnih koraka rezonovanja.
      </div>
    </section>

    <!-- AKCIJE -->
    <div class="result-actions">
      <button
        type="button"
        class="action-button secondary"
        @click="prosiriCinjenicama"
      >
        Proširi činjenicama
      </button>

      <button
        type="button"
        class="action-button primary"
        @click="novoRezonovanje"
      >
        Novo rezonovanje
      </button>
    </div>
  </div>
</template>


<style scoped>
.result-page {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 30px;
}

.message {
  padding: 15px 20px;
  margin-bottom: 20px;
  border-radius: 8px;
  background: #f3f4f6;
  color: #374151;
}

.conclusion-card {
  padding: 25px;
  margin-bottom: 30px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.conclusion-label {
  margin-bottom: 10px;
  font-size: 14px;
  color: #141414;
}

.conclusion-status {
  font-size: 26px;
  font-weight: 700;
}

.status-obaveza {
  color: #2563eb;
}

.status-zabrana {
  color: #dc2626;
}

.status-dozvola {
  color: #16a34a;
}

.status-povreda {
  color: #dc2626;
}

.status-nema-povrede {
  color: #16a34a;
}

.status-neprimenjivo {
  color: #6b7280;
}

.status-neodredjeno {
  color: #d97706;
}

.status-sukob {
  color: #9333ea;
}

.steps-section {
  margin-top: 30px;
}

.steps-section h2 {
  margin-bottom: 20px;
}

.step-card {
  display: flex;
  gap: 20px;
  margin-bottom: 18px;
  padding: 20px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 7px rgba(0, 0, 0, 0.07);
}

.step-number {
  min-width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e5e7eb;
  font-weight: 700;
}

.step-content {
  flex: 1;
}

.step-type {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
}

.step-content h3 {
  margin: 0 0 15px 0;
  font-size: 17px;
  color: #141414;
  line-height: 1.5;
}

.detail {
  margin-top: 12px;
}

.detail-label {
  display: block;
  margin-bottom: 5px;
  font-size: 13px;
  font-weight: 600;
  color: #555;
}

code {
  display: inline-block;
  padding: 4px 7px;
  border-radius: 4px;
  color: #141414;
  background: #f3f4f6;
  font-family: monospace;
}

.empty-state {
  padding: 30px;
  text-align: center;
  color: #777;
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
  padding-bottom: 30px;
}

.action-button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.2s;
}

.action-button.primary {
  background: #2c3e50;
  color: white;
}

.action-button.primary:hover {
  background: #1f2d3a;
}

.action-button.secondary {
  background: #ecf0f1;
  color: #2c3e50;
}

.action-button.secondary:hover {
  background: #dfe6e9;
}
</style>