/** 纯前端数据层的公共类型：与全栈版后端返回的结构保持一致，换回后端时页面不用改。 */

export type EntryRow = {
  id: number
  status: string
  pending: boolean
  abnormal: boolean
  [field: string]: string | number | boolean
}

export type ModuleMeta = {
  key: string
  name: string
  entity: string
  desc: string
  fields: string[]
  statuses: string[]
  actions: string[]
  actionTargets: Record<string, string>
  metrics: string[]
}

export type PageResult = {
  items: EntryRow[]
  total: number
  page: number
  size: number
}

export type ActionResult = {
  ok: boolean
  message: string
}

export type OverviewResult = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

export type EmergencyActionResult = {
  ok: boolean
  message: string
  granted?: boolean
  entry?: EntryRow
}

export type EmergencyRouteStep = {
  receipt_id: number
  登记编号: string
  换向点位: string
  目标方向: string
  临时牌编号: string
  申请班组: string
}

export type EmergencyRouteResult = {
  ok: boolean
  message: string
  count: number
  route: EmergencyRouteStep[]
}

export type EmergencyInstalledSign = {
  receipt_id: number
  登记编号: string
  换向点位: string
  目标方向: string
  临时牌编号: string
  申请班组: string
  当前状态: string
  安装时间: number | null
  安装结果: string
  安装人: string
}

export type EmergencyInstalledResult = {
  ok: boolean
  message: string
  count: number
  installed: EmergencyInstalledSign[]
}

export type EmergencyRejection = {
  receipt_id: number
  登记编号: string
  事故单号: string
  申请班组: string
  换向点位: string
  目标方向: string
  拒绝原因: string
  拒绝时间: number | null
}

export type EmergencyRejectionsResult = {
  count: number
  rejections: EmergencyRejection[]
}

export type EmergencyResolveResult = {
  ok: boolean
  message: string
  count: number
}
