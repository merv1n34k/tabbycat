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
        <div
          class="card h-100"
          :class="{
            'border-warning': hasConflict(team),
            'border-primary': dragOverTeam === team.id
          }"
          @dragover.prevent="onDragOver(team)"
          @dragleave="onDragLeave"
          @drop="onDrop($event, team)"
        >
          <div class="card-header py-2">
            <strong>{{ team.name }}</strong>
          </div>
          <ul class="list-group list-group-flush">
            <li
              v-for="speaker in team.speakers"
              :key="speaker.id"
              class="list-group-item py-2 px-3 d-flex justify-content-between align-items-center speaker-item"
              :class="{'dragging': isDragging(speaker)}"
              draggable="true"
              @dragstart="onDragStart($event, speaker, team)"
              @dragend="onDragEnd"
            >
              <span>{{ speaker.name }}</span>
              <span
                v-if="getPairCount(speaker, team)"
                class="badge badge-warning badge-pill"
                :title="'Previously paired ' + getPairCount(speaker, team) + ' time(s) with current teammate'"
              >
                {{ getPairCount(speaker, team) }}x paired
              </span>
            </li>
          </ul>
          <div
            v-if="draggedSpeaker && draggedFromTeam && draggedFromTeam.id !== team.id"
            class="card-footer text-center py-2 drop-hint"
            :class="{'drop-hint-active': dragOverTeam === team.id}"
          >
            Drop here
          </div>
        </div>
      </div>
    </div>

    <!-- Save button (sticky at bottom) -->
    <div v-if="isDirty" class="fixed-bottom bg-white border-top p-3 text-right shadow-sm">
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
      event.dataTransfer.setData('text/plain', speaker.id)
    },
    onDragEnd() {
      this.draggedSpeaker = null
      this.draggedFromTeam = null
      this.dragOverTeam = null
    },
    onDragOver(team) {
      if (this.draggedFromTeam && this.draggedFromTeam.id !== team.id) {
        this.dragOverTeam = team.id
      }
    },
    onDragLeave() {
      this.dragOverTeam = null
    },
    onDrop(event, targetTeam) {
      this.dragOverTeam = null
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
          if (this.pairHistory[key]) return true
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

<style scoped>
.speaker-item {
  cursor: grab;
  transition: background-color 0.15s, opacity 0.15s;
}
.speaker-item:hover {
  background-color: #f0f0f0;
}
.speaker-item.dragging {
  opacity: 0.4;
  background-color: #cce5ff;
}
.drop-hint {
  color: #6c757d;
  border-top: 2px dashed #dee2e6;
  font-size: 0.85em;
}
.drop-hint-active {
  color: #007bff;
  border-top-color: #007bff;
  background-color: #e7f3ff;
}
</style>
