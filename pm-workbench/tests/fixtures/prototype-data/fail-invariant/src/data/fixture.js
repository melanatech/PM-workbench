export const asOf = '2026-10-14'

export const tasks = [
  { id: 't1', status: 'open', points: 2, openedOn: '2026-10-01' },
  { id: 't2', status: 'open', points: 3, openedOn: '2026-10-10' },
  { id: 't3', status: 'done', points: 5, openedOn: '2026-10-12' },
  { id: 't4', status: 'blocked', points: 1, openedOn: '2026-10-11' },
]

export const sessions = [
  { id: 's1', taskId: 't1', minutes: 30, on: '2026-10-13' },
  { id: 's2', taskId: 't2', minutes: 15, on: '2026-10-14' },
]
