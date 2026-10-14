import { asOf, sessions, tasks } from './fixture.js'
import {
  doneTaskCount,
  openRate,
  openTaskCount,
  sessionMinutes,
  taskCount,
} from './selectors.js'

function assertInvariant(ok, message) {
  if (!ok) {
    console.error(`Invariant failed: ${message}`)
    process.exit(1)
  }
}

const open = openTaskCount()
const done = doneTaskCount()
const total = taskCount()

assertInvariant(
  open + done === total,
  `parts sum: open (${open}) + done (${done}) !== total (${total})`,
)
assertInvariant(open <= total, 'filtered open subset is larger than all tasks')
assertInvariant(done <= total, 'filtered done subset is larger than all tasks')

const rate = openRate()
assertInvariant(rate >= 0 && rate <= 1, `open rate out of bounds: ${rate}`)

const minutes = sessionMinutes()
const minuteSum = sessions.reduce((sum, row) => sum + row.minutes, 0)
assertInvariant(minutes === minuteSum, `session minutes ${minutes} !== ${minuteSum}`)

for (const task of tasks) {
  assertInvariant(task.openedOn <= asOf, `${task.id} opened after asOf ${asOf}`)
}
for (const session of sessions) {
  assertInvariant(session.on <= asOf, `${session.id} is after asOf ${asOf}`)
}

console.log('invariants ok')
