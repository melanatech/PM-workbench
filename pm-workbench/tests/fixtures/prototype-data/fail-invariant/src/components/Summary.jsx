import { openTaskCount, taskCount } from '../data/selectors.js'

export function Summary() {
  return (
    <section>
      <h1>Tasks</h1>
      <span data-metric="openCount">{openTaskCount()}</span>
      <span data-metric="taskCount">{taskCount()}</span>
    </section>
  )
}
