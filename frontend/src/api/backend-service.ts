import { request } from './client'
import { moduleMeta } from '@/data/modules'
import type {
  ActionResult,
  EmergencyActionResult,
  EmergencyInstalledResult,
  EmergencyRejectionsResult,
  EmergencyResolveResult,
  EmergencyRouteResult,
  EntryRow,
  OverviewResult,
  PageResult,
} from '@/data/types'

export { moduleMeta }

export async function listEntries(
  key: string,
  filters: Record<string, string> = {},
): Promise<PageResult> {
  const query = new URLSearchParams(filters).toString()
  const response = await request(`/api/${key}?${query}`)
  if (!response.ok) throw new Error('业务数据读取失败')
  return await response.json()
}

export async function createEntry(
  key: string,
  values: Record<string, string>,
): Promise<ActionResult> {
  const response = await request(`/api/${key}`, {
    method: 'POST',
    body: JSON.stringify({ values }),
  })
  return await response.json()
}

export async function runAction(
  key: string,
  id: number,
  action: string,
): Promise<ActionResult> {
  const response = await request(`/api/${key}/${id}/actions`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
  return await response.json()
}

export async function downloadEntries(
  key: string,
  filters: Record<string, string> = {},
): Promise<void> {
  const query = new URLSearchParams(filters).toString()
  const response = await request(`/api/${key}/export?${query}`)
  if (!response.ok) throw new Error('业务数据导出失败')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${key}.csv`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export async function loadOverview(): Promise<OverviewResult> {
  const response = await request('/api/overview')
  if (!response.ok) throw new Error('运营概览读取失败')
  return await response.json()
}

// ---------- 事故临时导视授权 ----------

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = (data as { detail?: unknown }).detail
    throw new Error(typeof detail === 'string' ? detail : `接口返回 ${response.status}`)
  }
  return data as T
}

export async function authorizeReceipt(id: number): Promise<EmergencyActionResult> {
  return parseResponse(await request(`/api/emergency/receipts/${id}/authorize`, { method: 'POST' }))
}

export async function installReceipt(id: number, installNote: string): Promise<EmergencyActionResult> {
  return parseResponse(
    await request(`/api/emergency/receipts/${id}/install`, {
      method: 'POST',
      body: JSON.stringify({ install_note: installNote }),
    }),
  )
}

export async function canInstallReceipt(id: number): Promise<{ ok: boolean; message: string }> {
  return parseResponse(await request(`/api/emergency/receipts/${id}/can-install`))
}

export async function resolveIncident(ref: string): Promise<EmergencyResolveResult> {
  return parseResponse(
    await request(`/api/emergency/incidents/${encodeURIComponent(ref)}/resolve`, { method: 'POST' }),
  )
}

export async function passageRoute(ref: string): Promise<EmergencyRouteResult> {
  return parseResponse(await request(`/api/emergency/incidents/${encodeURIComponent(ref)}/route`))
}

export async function installedSigns(ref: string): Promise<EmergencyInstalledResult> {
  return parseResponse(
    await request(`/api/emergency/incidents/${encodeURIComponent(ref)}/installed-signs`),
  )
}

export async function emergencyRejections(): Promise<EmergencyRejectionsResult> {
  return parseResponse(await request('/api/emergency/rejections'))
}
