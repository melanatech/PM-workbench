import { openTaskCount } from '../data/selectors.js'

export function Detail() {
  return (
    <section>
      <h1>Open tasks</h1>
      <span data-metric="openCount">{openTaskCount()}</span>
    </section>
  )
}
