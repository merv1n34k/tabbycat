<script setup>
import _ from 'lodash'
import { useAjax } from '../composables/useAjax.js'

const props = defineProps({
  cellData: Object,
})

const emit = defineEmits(['toggle-checked', 'update-sort', 'update-checked'])

const { ajaxSave } = useAjax()

const updateChecked = (value) => {
  emit('update-checked', { id: props.cellData.id, checked: value })
}

const checkUpdate = () => {
  if (props.cellData.noSave) {
    return
  }
  const cd = props.cellData
  const checked = cd.checked
  if (_.isUndefined(props.cellData.saveURL)) {
    emit('toggle-checked', cd)
  } else {
    const message = `${cd.id}'s ${cd.type} status as ${checked}`
    const payload = { id: cd.id }
    payload[cd.type] = checked
    ajaxSave(cd.saveURL, payload, message, null, null, null)
  }
  emit('update-sort', { id: cd.id, sort: checked })
}
</script>

<template>
  <td :class="cellData.class ? cellData.class : null">
    <span
      v-if="cellData.sort"
      hidden
    >
      {{ cellData.checked }}
    </span>
    <div class="table-check">
      <input
        :checked="cellData.checked"
        type="checkbox"
        class="form-check-input position-static"
        :name="cellData.name"
        :value="cellData.value"
        @change="updateChecked($event.target.checked); checkUpdate()"
      >
    </div>
  </td>
</template>
