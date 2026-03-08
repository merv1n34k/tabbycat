<template>
  <div class="mt-3" :style="{ paddingBottom: isDirty ? '90px' : '0' }">
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
        <!-- Team as a droppable zone (uses global .vue-droppable styles) -->
        <div
          class="vue-droppable h-100 border rounded"
          :class="{
            'vue-droppable-enter': dragOverTeam === team.id,
            'border-warning': hasConflict(team) && dragOverTeam !== team.id,
          }"
          @dragover.prevent
          @drop.prevent.stop="onDrop($event, team)"
          @dragenter="onDragEnter($event, team)"
          @dragleave="onDragLeave"
        >
          <!-- Team header -->
          <div class="border-bottom p-2 bg-white d-flex justify-content-between align-items-center">
            <strong>{{ team.name }}</strong>
            <span class="badge badge-secondary">{{ team.speakers.length }}</span>
          </div>

          <!-- Speaker items using allocation .vue-draggable pattern -->
          <div class="p-1">
            <div
              v-for="speaker in team.speakers"
              :key="speaker.id"
              class="vue-draggable d-flex m-1 align-items-center align-self-center"
              :class="{ 'vue-draggable-dragging': isDragging(speaker) }"
              draggable="true"
              @dragstart="onDragStart($event, speaker, team)"
              @dragend="onDragEnd"
            >
              <div class="py-1 pl-2 pr-2 d-flex flex-column flex-truncate flex-fill">
                <h5 class="mb-0 vc-title text-truncate">{{ speaker.name }}</h5>
                <h6
                  v-if="getPairCount(speaker, team) >= 2"
                  class="mb-0 vue-draggable-muted vc-subtitle text-truncate"
                >
                  {{ getPairCount(speaker, team) }}x paired together
                </h6>
              </div>
            </div>
          </div>

          <!-- Drop hint visible while dragging -->
          <div
            v-if="draggedSpeaker && draggedFromTeam && draggedFromTeam.id !== team.id"
            class="text-center py-2 small border-top"
            :class="dragOverTeam === team.id ? 'text-white' : 'text-muted'"
          >
            Drop here
          </div>
        </div>
      </div>
    </div>

    <!-- Save button bar (fixed at bottom) -->
    <div v-if="isDirty" class="fixed-bottom bg-white border-top p-3 text-right shadow-sm" style="z-index: 1030;">
      <button class="btn btn-success btn-lg" @click="saveAssignments">
        Save Changes
      </button>
      <button class="btn btn-outline-secondary btn-lg ml-2" @click="resetAssignments">
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
  methods: {
    isDragging(speaker) {
      return this.draggedSpeaker && this.draggedSpeaker.id === speaker.id
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
    hasConflict(team) {
      const speakers = team.speakers
      for (let i = 0; i < speakers.length; i++) {
        for (let j = i + 1; j < speakers.length; j++) {
          const key = `${Math.min(speakers[i].id, speakers[j].id)}-${Math.max(speakers[i].id, speakers[j].id)}`
          if ((this.pairHistory[key] || 0) >= 2) return true
        }
      }
      return false
    },
    getPairCount(speaker, team) {
      let count = 0
      for (const other of team.speakers) {
        if (other.id === speaker.id) continue
        const key = `${Math.min(speaker.id, other.id)}-${Math.max(speaker.id, other.id)}`
        count += this.pairHistory[key] || 0
      }
      return count
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
