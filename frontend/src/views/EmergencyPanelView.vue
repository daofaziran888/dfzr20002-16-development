<template>
  <section class="page" data-module="emergency">
    <header class="page-head">
      <div>
        <h2>应急通行面板</h2>
        <p class="page-desc">
          凭事故单办理临时换向：授权只覆盖事故单所属场馆，越权申请记录拒绝；
          同一时刻同一点位只允许一个生效方向，先交回安装回执者生效；
          解除事故后仍可查回旧路线上实际安装过的临时牌。
        </p>
      </div>
    </header>

    <form class="filter-bar" @submit.prevent="reloadAll">
      <label class="filter-item">
        <span>事故单号</span>
        <input v-model="incidentRef" data-testid="incident-ref" placeholder="如 INCI-0002" />
      </label>
      <button class="btn primary" data-testid="load" type="submit">查询事故单</button>
      <button class="btn ghost" data-testid="resolve" type="button" @click="onResolve">解除事故</button>
    </form>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="notice" class="ok-text">{{ notice }}</p>

    <h3 class="section-title">换向回执</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>登记编号</th><th>申请班组</th><th>换向点位</th><th>目标方向</th>
          <th>临时牌编号</th><th>当前状态</th><th>办理</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in receipts" :key="String(row.id)" :data-testid="`receipt-${row.id}`">
          <td>{{ row['登记编号'] }}</td>
          <td>{{ row['申请班组'] }}</td>
          <td>{{ row['换向点位'] }}</td>
          <td>{{ row['目标方向'] }}</td>
          <td>{{ row['临时牌编号'] }}</td>
          <td>{{ row.status }}</td>
          <td class="row-actions">
            <button
              v-if="row.status === '已申请'"
              class="link"
              type="button"
              :data-testid="`authorize-${row.id}`"
              @click="onAuthorize(Number(row.id))"
            >授权换向</button>
            <template v-if="row.status === '已授权'">
              <input
                v-model="installNotes[Number(row.id)]"
                class="install-input"
                placeholder="安装结果说明"
                :data-testid="`install-note-${row.id}`"
              />
              <button
                class="link"
                type="button"
                :data-testid="`install-${row.id}`"
                @click="onInstall(Number(row.id))"
              >交回安装回执</button>
              <button
                class="link"
                type="button"
                :data-testid="`can-install-${row.id}`"
                @click="onCanInstall(Number(row.id))"
              >可否安装</button>
            </template>
          </td>
        </tr>
        <tr v-if="!receipts.length">
          <td colspan="7" class="empty-state">该事故单暂无换向回执，可先到「事故临时导视授权」登记</td>
        </tr>
      </tbody>
    </table>

    <h3 class="section-title">现场通行路线（按生效回执发布）</h3>
    <table class="data-table">
      <thead>
        <tr><th>换向点位</th><th>生效方向</th><th>临时牌编号</th><th>申请班组</th><th>回执编号</th></tr>
      </thead>
      <tbody>
        <tr v-for="step in route" :key="step.receipt_id" data-testid="route-step">
          <td>{{ step.换向点位 }}</td>
          <td>{{ step.目标方向 }}</td>
          <td>{{ step.临时牌编号 }}</td>
          <td>{{ step.申请班组 }}</td>
          <td>{{ step.登记编号 }}</td>
        </tr>
        <tr v-if="!route.length">
          <td colspan="5" class="empty-state">当前无生效换向回执，暂无应急通行路线</td>
        </tr>
      </tbody>
    </table>

    <h3 class="section-title">实际安装过的临时牌（含已解除的旧路线）</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>临时牌编号</th><th>换向点位</th><th>方向</th><th>申请班组</th>
          <th>安装结果</th><th>安装人</th><th>安装时间</th><th>当前状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="sign in installed" :key="sign.receipt_id" data-testid="installed-sign">
          <td>{{ sign.临时牌编号 }}</td>
          <td>{{ sign.换向点位 }}</td>
          <td>{{ sign.目标方向 }}</td>
          <td>{{ sign.申请班组 }}</td>
          <td>{{ sign.安装结果 }}</td>
          <td>{{ sign.安装人 }}</td>
          <td>{{ formatTime(sign.安装时间) }}</td>
          <td>{{ sign.当前状态 }}</td>
        </tr>
        <tr v-if="!installed.length">
          <td colspan="8" class="empty-state">该事故单暂无实际安装记录</td>
        </tr>
      </tbody>
    </table>

    <h3 class="section-title">越权拒绝记录</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>回执编号</th><th>事故单号</th><th>申请班组</th><th>换向点位</th>
          <th>目标方向</th><th>拒绝原因</th><th>拒绝时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in rejections" :key="item.receipt_id" data-testid="rejection-row">
          <td>{{ item.登记编号 }}</td>
          <td>{{ item.事故单号 }}</td>
          <td>{{ item.申请班组 }}</td>
          <td>{{ item.换向点位 }}</td>
          <td>{{ item.目标方向 }}</td>
          <td>{{ item.拒绝原因 }}</td>
          <td>{{ formatTime(item.拒绝时间) }}</td>
        </tr>
        <tr v-if="!rejections.length">
          <td colspan="7" class="empty-state">暂无越权拒绝记录</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  authorizeReceipt,
  canInstallReceipt,
  emergencyRejections,
  installReceipt,
  installedSigns,
  listEntries,
  passageRoute,
  resolveIncident,
} from '@/api/backend-service'
import type {
  EmergencyInstalledSign,
  EmergencyRejection,
  EmergencyRouteStep,
  EntryRow,
} from '@/data/types'

const incidentRef = ref('INCI-0002')
const receipts = ref<EntryRow[]>([])
const route = ref<EmergencyRouteStep[]>([])
const installed = ref<EmergencyInstalledSign[]>([])
const rejections = ref<EmergencyRejection[]>([])
const installNotes = ref<Record<number, string>>({})
const errorMessage = ref('')
const notice = ref('')

function formatTime(ts: number | null): string {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

function clearMessages() {
  errorMessage.value = ''
  notice.value = ''
}

async function reloadAll() {
  clearMessages()
  const ref = incidentRef.value.trim()
  if (!ref) {
    errorMessage.value = '请先填写事故单号'
    return
  }
  try {
    const page = await listEntries('emergency_signage', { 事故单号: ref })
    receipts.value = page.items
    const [routeResult, installedResult, rejectionResult] = await Promise.all([
      passageRoute(ref),
      installedSigns(ref),
      emergencyRejections(),
    ])
    route.value = routeResult.route
    installed.value = installedResult.installed
    rejections.value = rejectionResult.rejections
    notice.value = routeResult.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '查询失败'
  }
}

async function onAuthorize(id: number) {
  clearMessages()
  try {
    const result = await authorizeReceipt(id)
    notice.value = result.message
    if (result.granted === false) {
      errorMessage.value = result.message
      notice.value = ''
    }
    await reloadAll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '授权失败'
  }
}

async function onInstall(id: number) {
  clearMessages()
  try {
    const result = await installReceipt(id, installNotes.value[id] ?? '')
    notice.value = result.message
    installNotes.value[id] = ''
    await reloadAll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '安装回执提交失败'
  }
}

async function onCanInstall(id: number) {
  clearMessages()
  try {
    const result = await canInstallReceipt(id)
    if (result.ok) {
      notice.value = result.message
    } else {
      errorMessage.value = result.message
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '预检失败'
  }
}

async function onResolve() {
  clearMessages()
  const ref = incidentRef.value.trim()
  if (!ref) {
    errorMessage.value = '请先填写事故单号'
    return
  }
  try {
    const result = await resolveIncident(ref)
    notice.value = result.message
    await reloadAll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '解除事故失败'
  }
}

onMounted(reloadAll)
</script>

<style scoped>
.section-title {
  font-size: 14px;
  margin: 16px 0 8px;
}

.ok-text {
  color: #15803d;
}

.install-input {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  width: 130px;
}
</style>
