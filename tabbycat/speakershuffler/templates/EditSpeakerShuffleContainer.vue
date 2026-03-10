<template>
  <div class="mt-3">
    <!-- Status bar -->
    <div v-if="saveStatus" class="alert" :class="saveStatusClass" role="alert">
      {{ saveStatus }}
    </div>

    <!-- Empty state -->
    <div v-if="teams.length === 0" class="text-center text-muted py-5">
      <p>No speaker assignments to display.</p>
    </div>

    <!-- Teams grid -->
    <div v-else class="row">
      <div
        v-for="team in teams"
        :key="team.id"
        class="col-lg-3 col-md-4 col-sm-6 mb-3"
      >
        <!-- Team as a droppable zone -->
        <div
          class="vue-droppable h-100 border rounded"
          :class="{
            'vue-droppable-enter': dragOverTeam === team.id,
          }"
          @dragover.prevent
          @drop.prevent.stop="onDrop($event, team)"
          @dragenter="onDragEnter($event, team)"
          @dragleave="onDragLeave"
        >
          <!-- Team header -->
          <div
            class="border-bottom p-2 d-flex justify-content-between align-items-center"
            :class="team.speakers.length > speakersPerTeam ? 'bg-danger text-white' : 'bg-white'"
          >
            <strong>{{ team.name }}</strong>
            <span class="badge" :class="team.speakers.length > speakersPerTeam ? 'badge-light' : 'badge-secondary'">{{ team.speakers.length }}</span>
          </div>

          <!-- Speaker items -->
          <div class="p-1">
            <div
              v-for="speaker in team.speakers"
              :key="speaker.id"
              class="vue-draggable d-flex m-1 align-items-center align-self-center"
              :class="[
                { 'vue-draggable-dragging': isDragging(speaker) },
                getSpeakerCSS(speaker),
              ]"
              style="position: relative; overflow: hidden;"
              draggable="true"
              @dragstart="onDragStart($event, speaker, team)"
              @dragend="onDragEnd"
            >
              <h4 v-if="getSpeakerPoints(speaker)" class="mb-0 py-1 text-monospace vc-draggable-number vc-number">
                <small class="pl-2 vue-draggable-muted">{{ getSpeakerPoints(speaker) }}<template v-if="getSpeakerWeightedScore(speaker)"> / {{ getSpeakerWeightedScore(speaker) }}</template></small>
              </h4>
              <div class="py-1 pl-2 pr-2 d-flex flex-column flex-truncate flex-fill">
                <h5 class="mb-0 vc-title text-truncate">{{ speaker.name }}</h5>
              </div>
              <div v-if="getSpeakerHistory(speaker)" class="history-tooltip" style="position: absolute; bottom: 0; right: 0; z-index: 1; pointer-events: none;">
                <div :class="['tooltip-inner conflictable', 'hover-histories-' + getSpeakerHistory(speaker) + '-ago']" style="opacity: 1;">
                  {{ getSpeakerHistory(speaker) }} ago<template v-if="getSpeakerHistoryCount(speaker) > 1"> &times; {{ getSpeakerHistoryCount(speaker) }}</template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Auto-save on change -->
    <div v-if="isDirty" class="mt-3 text-right">
      <button class="btn btn-success" @click="saveAssignments">
        Save Changes
      </button>
      <button class="btn btn-outline-secondary ml-2" @click="resetAssignments">
        Reset
      </button>
    </div>
  </div>
</template>

<script>
function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return ''
}

export default {
  name: 'EditSpeakerShuffleContainer',
  props: {
    initialTeams: {
      type: Array,
      required: true,
    },
    pairHistory: {
      type: Object,
      default: () => ({}),
    },
    speakerConflicts: {
      type: Object,
      default: () => ({}),
    },
    speakerPoints: {
      type: Object,
      default: () => ({}),
    },
    speakerWeightedScores: {
      type: Object,
      default: () => ({}),
    },
    speakersPerTeam: {
      type: Number,
      default: 2,
    },
    saveUrl: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      teams: JSON.parse(JSON.stringify(this.initialTeams)),
      originalTeams: JSON.parse(JSON.stringify(this.initialTeams)),
      draggedSpeaker: null,
      draggedFromTeam: null,
      dragOverTeam: null,
      dragCounter: 0,
      isDirty: false,
      saveStatus: null,
      saveStatusClass: 'alert-info',
    }
  },
  computed: {
    // Build per-speaker conflict/history data based on current team assignments
    speakerConflictData() {
      const result = {}
      for (const team of this.teams) {
        for (const speaker of team.speakers) {
          let bestClash = false
          let bestAgo = null
          let bestCount = 0
          for (const other of team.speakers) {
            if (other.id === speaker.id) continue
            const key = `${Math.min(speaker.id, other.id)}-${Math.max(speaker.id, other.id)}`
            // Check personal conflict (highest priority)
            if (this.speakerConflicts[key]) {
              bestClash = true
            }
            // Check history
            const hist = this.pairHistory[key]
            if (hist) {
              if (bestAgo === null || hist.ago < bestAgo) {
                bestAgo = hist.ago
                bestCount = hist.count
              } else if (hist.ago === bestAgo && hist.count > bestCount) {
                bestCount = hist.count
              }
            }
          }
          if (bestClash) {
            result[speaker.id] = { css: 'conflictable panel-adjudicator', hasClash: true, ago: bestAgo, count: bestCount }
          } else if (bestAgo !== null) {
            result[speaker.id] = { css: `conflictable panel-histories-${bestAgo}-ago`, hasClash: false, ago: bestAgo, count: bestCount }
          }
        }
      }
      return result
    },
  },
  methods: {
    isDragging(speaker) {
      return this.draggedSpeaker && this.draggedSpeaker.id === speaker.id
    },
    getSpeakerCSS(speaker) {
      const data = this.speakerConflictData[speaker.id]
      return data ? data.css : ''
    },
    getSpeakerHistory(speaker) {
      const data = this.speakerConflictData[speaker.id]
      return (data && data.ago !== null) ? data.ago : false
    },
    getSpeakerHistoryCount(speaker) {
      const data = this.speakerConflictData[speaker.id]
      return data ? data.count : 0
    },
    getSpeakerPoints(speaker) {
      const pts = this.speakerPoints[String(speaker.id)]
      if (pts == null) return null
      return Number.isInteger(pts) ? String(pts) : pts.toFixed(1)
    },
    getSpeakerWeightedScore(speaker) {
      const ws = this.speakerWeightedScores[String(speaker.id)]
      if (ws == null) return null
      return Number.isInteger(ws) ? String(ws) : ws.toFixed(1)
    },
    hasConflict(team) {
      for (const speaker of team.speakers) {
        if (this.speakerConflictData[speaker.id]) return true
      }
      return false
    },
    onDragStart(event, speaker, team) {
      this.draggedSpeaker = speaker
      this.draggedFromTeam = team
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', JSON.stringify({
        speakerId: speaker.id,
        fromTeamId: team.id,
      }))
    },
    onDragEnd() {
      this.draggedSpeaker = null
      this.draggedFromTeam = null
      this.dragOverTeam = null
      this.dragCounter = 0
    },
    onDragEnter(event, team) {
      if (this.draggedFromTeam && this.draggedFromTeam.id !== team.id) {
        this.dragCounter += 1
        this.dragOverTeam = team.id
      }
    },
    onDragLeave() {
      this.dragCounter -= 1
      if (this.dragCounter <= 0) {
        this.dragOverTeam = null
        this.dragCounter = 0
      }
    },
    onDrop(event, targetTeam) {
      this.dragOverTeam = null
      this.dragCounter = 0
      if (!this.draggedSpeaker || !this.draggedFromTeam) return
      if (this.draggedFromTeam.id === targetTeam.id) return

      const sourceTeam = this.teams.find(t => t.id === this.draggedFromTeam.id)
      const destTeam = this.teams.find(t => t.id === targetTeam.id)
      if (!sourceTeam || !destTeam) return

      const speakerIdx = sourceTeam.speakers.findIndex(s => s.id === this.draggedSpeaker.id)
      if (speakerIdx === -1) return

      const [speaker] = sourceTeam.speakers.splice(speakerIdx, 1)
      destTeam.speakers.push(speaker)

      this.isDirty = true
      this.draggedSpeaker = null
      this.draggedFromTeam = null
    },
    resetAssignments() {
      this.teams = JSON.parse(JSON.stringify(this.originalTeams))
      this.isDirty = false
      this.saveStatus = null
    },
    async saveAssignments() {
      const assignments = {}
      for (const team of this.teams) {
        for (const speaker of team.speakers) {
          assignments[speaker.id] = team.id
        }
      }

      this.saveStatus = 'Saving...'
      this.saveStatusClass = 'alert-info'

      try {
        const response = await fetch(this.saveUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: JSON.stringify({ assignments }),
        })
        const data = await response.json()
        if (data.status === 'ok') {
          this.saveStatus = 'Saved successfully!'
          this.saveStatusClass = 'alert-success'
          this.isDirty = false
          this.originalTeams = JSON.parse(JSON.stringify(this.teams))
          setTimeout(() => { this.saveStatus = null }, 3000)
        } else {
          this.saveStatus = 'Save failed: ' + (data.message || 'Unknown error')
          this.saveStatusClass = 'alert-danger'
        }
      } catch (err) {
        this.saveStatus = 'Save failed: ' + err.message
        this.saveStatusClass = 'alert-danger'
      }
    },
  },
}
</script>
