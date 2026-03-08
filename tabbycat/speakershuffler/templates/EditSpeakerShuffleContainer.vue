<template>
  <div class="container-fluid mt-3">
    <!-- Status bar -->
    <div v-if="saveStatus" class="alert" :class="saveStatusClass" role="alert">
      {{ saveStatus }}
    </div>

    <!-- Teams grid -->
    <div class="row">
      <div
        v-for="team in teams"
        :key="team.id"
        class="col-lg-3 col-md-4 col-sm-6 mb-3"
      >
        <div class="card h-100" :class="{'border-warning': hasConflict(team)}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <strong>{{ team.name }}</strong>
            <span class="badge badge-secondary">{{ team.speakers.length }} speakers</span>
          </div>
          <div class="card-body p-2">
            <div
              v-for="speaker in team.speakers"
              :key="speaker.id"
              class="speaker-card p-2 mb-1 rounded d-flex justify-content-between align-items-center"
              :class="{'bg-light': !isDragging(speaker), 'bg-info text-white': isDragging(speaker)}"
              draggable="true"
              @dragstart="onDragStart($event, speaker, team)"
              @dragend="onDragEnd"
            >
              <span>
                <i data-feather="user" style="width:14px;height:14px"></i>
                {{ speaker.name }}
              </span>
              <span v-if="getPairCount(speaker, team)" class="badge badge-warning" :title="'Previously paired ' + getPairCount(speaker, team) + ' time(s)'">
                {{ getPairCount(speaker, team) }}x
              </span>
            </div>
            <!-- Drop zone -->
            <div
              class="drop-zone p-2 text-center text-muted rounded mt-1"
              :class="{'drop-zone-active': dragOverTeam === team.id}"
              @dragover.prevent="onDragOver(team)"
              @dragleave="onDragLeave"
              @drop="onDrop($event, team)"
            >
              <i data-feather="plus-circle" style="width:14px;height:14px"></i>
              Drop speaker here
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Save button -->
    <div class="fixed-bottom bg-white border-top p-3 text-right" v-if="isDirty">
      <button class="btn btn-success btn-lg" @click="saveAssignments">
        <i data-feather="save" style="width:16px;height:16px"></i>
        Save Changes
      </button>
    </div>
  </div>
</template>

<script>
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
    csrfToken: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      teams: JSON.parse(JSON.stringify(this.initialTeams)),
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
    },
    onDragEnd() {
      this.draggedSpeaker = null
      this.draggedFromTeam = null
      this.dragOverTeam = null
    },
    onDragOver(team) {
      this.dragOverTeam = team.id
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
            'X-CSRFToken': this.csrfToken,
          },
          body: JSON.stringify({ assignments }),
        })
        const data = await response.json()
        if (data.status === 'ok') {
          this.saveStatus = 'Saved successfully!'
          this.saveStatusClass = 'alert-success'
          this.isDirty = false
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
.speaker-card {
  cursor: grab;
  border: 1px solid #dee2e6;
  transition: background-color 0.15s;
}
.speaker-card:hover {
  background-color: #e9ecef !important;
}
.drop-zone {
  border: 2px dashed #dee2e6;
  min-height: 40px;
  transition: all 0.15s;
}
.drop-zone-active {
  border-color: #007bff;
  background-color: #e7f3ff;
}
</style>
