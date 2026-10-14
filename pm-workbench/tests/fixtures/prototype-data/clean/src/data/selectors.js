import { sessions, tasks } from './fixture.js'

export function openTaskCount(rows = tasks) {
  return rows.filter((row) => row.status === 'open').length
}

export function doneTaskCount(rows = tasks) {
  return rows.filter((row) => row.status === 'done').length
}

export function taskCount(rows = tasks) {
  return rows.length
}

export function sessionMinutes(rows = sessions) {
  return rows.reduce((total, row) => total + row.minutes, 0)
}

export function openRate(rows = tasks) {
  const total = taskCount(rows)
  if (total === 0) return 0
  return openTaskCount(rows) / total
}
