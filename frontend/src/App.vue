<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { createAccount, getAccounts, getUsage, updateAccount } from './api/usage'
import type { Account, UsageItem } from './types'

type AccountUsageState = {
  plan: UsageItem
  compensation: UsageItem
  loading: boolean
  error: string
}

const accounts = ref<Account[]>([])
const saving = ref(false)
const pageError = ref('')

const isModalOpen = ref(false)
const modalMode = ref<'add' | 'edit'>('add')
const editingAccountId = ref('')
const formName = ref('')
const formCookie = ref('')
let refreshTimer: number | null = null

const usageById = reactive<Record<string, AccountUsageState>>({})

function emptyItem(name: string): UsageItem {
  return { name, used: 0, limit: 0, percent: 0 }
}

function getUsageState(accountId: string): AccountUsageState {
  if (!usageById[accountId]) {
    usageById[accountId] = {
      plan: emptyItem('plan_total_token'),
      compensation: emptyItem('compensation_total_token'),
      loading: false,
      error: '',
    }
  }
  return usageById[accountId]
}

function fmt(n: number): string {
  const value = Number(n || 0)
  const abs = Math.abs(value)
  const units = [
    { unit: 'B', size: 1_000_000_000 },
    { unit: 'M', size: 1_000_000 },
    { unit: 'k', size: 1_000 },
  ]

  for (const item of units) {
    if (abs >= item.size) {
      const scaled = value / item.size
      const digits = Math.abs(scaled) >= 100 ? 0 : Math.abs(scaled) >= 10 ? 1 : 2
      return `${scaled.toFixed(digits)}${item.unit}`
    }
  }

  return value.toLocaleString('zh-CN')
}

function pct(used: number, limit: number, rawPercent: number): number {
  if (typeof rawPercent === 'number' && rawPercent > 0) return rawPercent * 100
  if (!limit) return 0
  return (used / limit) * 100
}

function totalPercent(plan: UsageItem, compensation: UsageItem): number {
  const totalUsed = Number(plan.used || 0) + Number(compensation.used || 0)
  const totalLimit = Number(plan.limit || 0) + Number(compensation.limit || 0)
  if (!totalLimit) return 0
  return (totalUsed / totalLimit) * 100
}

function totalLimit(plan: UsageItem, compensation: UsageItem): number {
  return Number(plan.limit || 0) + Number(compensation.limit || 0)
}

async function loadAccounts() {
  const res = await getAccounts()
  accounts.value = res.data.filter((x) => x.name !== '默认账号' && x.id !== 'default')
  if (!accounts.value.length) {
    throw new Error('没有可用账号，请先添加账号')
  }
}

async function refreshAccount(accountId: string) {
  const state = getUsageState(accountId)
  state.loading = true
  state.error = ''
  try {
    const res = await getUsage(accountId)
    state.plan = res.data.usage.plan
    state.compensation = res.data.usage.compensation
  } catch (e) {
    state.error = e instanceof Error ? e.message : '加载失败'
  } finally {
    state.loading = false
  }
}

async function refreshAll() {
  await Promise.all(accounts.value.map((x) => refreshAccount(x.id)))
}

function setupAutoRefresh() {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
  }
  refreshTimer = window.setInterval(() => {
    void refreshAll()
  }, 5 * 60 * 1000)
}

function openAddModal() {
  modalMode.value = 'add'
  editingAccountId.value = ''
  formName.value = ''
  formCookie.value = ''
  pageError.value = ''
  isModalOpen.value = true
}

function openEditModal(account: Account) {
  modalMode.value = 'edit'
  editingAccountId.value = account.id
  formName.value = account.name
  formCookie.value = ''
  pageError.value = ''
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
}

async function submitModal() {
  const name = formName.value.trim()
  const cookie = formCookie.value.trim()

  if (!name) {
    pageError.value = '请输入账号名称'
    return
  }
  if (!cookie) {
    pageError.value = '请输入账号 cookie'
    return
  }

  saving.value = true
  pageError.value = ''
  try {
    if (modalMode.value === 'add') {
      const created = await createAccount({ name, cookie })
      await loadAccounts()
      await refreshAccount(created.data.id)
    } else {
      await updateAccount(editingAccountId.value, { name, cookie })
      await loadAccounts()
      await refreshAccount(editingAccountId.value)
    }
    closeModal()
  } catch (e) {
    pageError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadAccounts()
    await refreshAll()
    setupAutoRefresh()
  } catch (e) {
    pageError.value = e instanceof Error ? e.message : '初始化失败'
  }
})

onUnmounted(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <div class="mx-auto grid max-w-6xl gap-4 p-4 md:p-6">
    <section class="rounded-2xl border border-neutral-300 bg-white p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="m-0 text-2xl font-semibold">小米 Token Plan 配额监控</h1>
          <p class="mt-1 text-sm text-neutral-500">多账号按页面顺序展示</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            class="min-h-10 rounded-full border border-neutral-300 bg-white px-4 text-sm font-semibold"
            @click="openAddModal"
          >
            添加账号
          </button>
          <button
            class="min-h-10 rounded-full border border-blue-600 bg-blue-600 px-4 text-sm font-semibold text-white"
            @click="refreshAll"
          >
            全部刷新
          </button>
        </div>
      </div>
      <p v-if="pageError" class="mt-3 text-sm text-red-600">{{ pageError }}</p>
    </section>

    <section
      v-for="account in accounts"
      :key="account.id"
      class="rounded-2xl border border-neutral-300 bg-white p-4"
    >
      <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 class="m-0 text-lg font-semibold">{{ account.name }}</h2>
        <div class="flex items-center gap-2">
          <button
            class="min-h-9 rounded-full border border-neutral-300 bg-white px-3 text-sm font-semibold"
            @click="openEditModal(account)"
          >
            编辑
          </button>
          <button
            class="min-h-9 rounded-full border border-blue-600 bg-blue-600 px-3 text-sm font-semibold text-white"
            :disabled="getUsageState(account.id).loading"
            @click="refreshAccount(account.id)"
          >
            {{ getUsageState(account.id).loading ? '刷新中...' : '刷新' }}
          </button>
        </div>
      </div>

      <p v-if="getUsageState(account.id).error" class="mb-3 text-sm text-red-600">
        {{ getUsageState(account.id).error }}
      </p>

      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-xl border border-neutral-300 p-4">
          <div class="mb-2 text-sm text-neutral-500">月度积分（used）</div>
          <p class="m-0 text-3xl font-semibold tabular-nums">{{ fmt(getUsageState(account.id).plan.used) }}</p>
        </div>
        <div class="rounded-xl border border-neutral-300 p-4">
          <div class="mb-2 text-sm text-neutral-500">补偿积分（used）</div>
          <p class="m-0 text-3xl font-semibold tabular-nums">{{ fmt(getUsageState(account.id).compensation.used) }}</p>
        </div>
        <div class="rounded-xl border border-neutral-300 p-4">
          <div class="mb-2 text-sm text-neutral-500">使用百分比（总）</div>
          <p class="m-0 text-3xl font-semibold tabular-nums">
            {{ totalPercent(getUsageState(account.id).plan, getUsageState(account.id).compensation).toFixed(2) }}%
          </p>
        </div>
        <div class="rounded-xl border border-neutral-300 p-4">
          <div class="mb-2 text-sm text-neutral-500">总量（limit）</div>
          <p class="m-0 text-3xl font-semibold tabular-nums">
            {{ fmt(totalLimit(getUsageState(account.id).plan, getUsageState(account.id).compensation)) }}
          </p>
        </div>
      </div>

      <div class="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div class="rounded-xl border border-neutral-300 p-4">
          <h3 class="m-0 text-base font-semibold">月度配额（plan_total_token）</h3>
          <div class="my-2 flex items-center justify-between text-sm text-neutral-500">
            <span>已用 / 上限</span>
            <span class="tabular-nums">
              {{ fmt(getUsageState(account.id).plan.used) }} / {{ fmt(getUsageState(account.id).plan.limit) }}
            </span>
          </div>
          <div class="h-3 overflow-hidden rounded-full border border-neutral-200 bg-neutral-100">
            <div
              class="h-full bg-gradient-to-r from-blue-600 to-blue-400 transition-all"
              :style="{ width: `${Math.min(pct(getUsageState(account.id).plan.used, getUsageState(account.id).plan.limit, getUsageState(account.id).plan.percent), 100).toFixed(2)}%` }"
            />
          </div>
          <div class="mt-2 text-xs text-neutral-500">
            使用率 {{ pct(getUsageState(account.id).plan.used, getUsageState(account.id).plan.limit, getUsageState(account.id).plan.percent).toFixed(2) }}%
          </div>
        </div>

        <div class="rounded-xl border border-neutral-300 p-4">
          <h3 class="m-0 text-base font-semibold">补偿配额（compensation_total_token）</h3>
          <div class="my-2 flex items-center justify-between text-sm text-neutral-500">
            <span>已用 / 上限</span>
            <span class="tabular-nums">
              {{ fmt(getUsageState(account.id).compensation.used) }} / {{ fmt(getUsageState(account.id).compensation.limit) }}
            </span>
          </div>
          <div class="h-3 overflow-hidden rounded-full border border-neutral-200 bg-neutral-100">
            <div
              class="h-full bg-gradient-to-r from-blue-600 to-blue-400 transition-all"
              :style="{ width: `${Math.min(pct(getUsageState(account.id).compensation.used, getUsageState(account.id).compensation.limit, getUsageState(account.id).compensation.percent), 100).toFixed(2)}%` }"
            />
          </div>
          <div class="mt-2 text-xs text-neutral-500">
            使用率 {{ pct(getUsageState(account.id).compensation.used, getUsageState(account.id).compensation.limit, getUsageState(account.id).compensation.percent).toFixed(2) }}%
          </div>
        </div>
      </div>
    </section>
  </div>

  <div
    v-if="isModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4"
    @click.self="closeModal"
  >
    <div class="w-full max-w-2xl rounded-2xl bg-white p-4 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="m-0 text-lg font-semibold">{{ modalMode === 'add' ? '添加账号' : '编辑账号' }}</h2>
        <button class="rounded-full border border-neutral-300 px-3 py-1 text-sm" @click="closeModal">关闭</button>
      </div>

      <div class="mt-3 grid grid-cols-1 gap-2">
        <input
          v-model="formName"
          class="min-h-10 rounded-xl border border-neutral-300 px-3 text-sm"
          placeholder="账号名称"
        />
        <textarea
          v-model="formCookie"
          class="min-h-28 rounded-xl border border-neutral-300 px-3 py-2 text-sm"
          placeholder="账号 cookie"
        />
      </div>

      <div class="mt-3 flex justify-end gap-2">
        <button class="rounded-full border border-neutral-300 bg-white px-4 py-2 text-sm" @click="closeModal">取消</button>
        <button
          class="rounded-full border border-blue-600 bg-blue-600 px-4 py-2 text-sm font-semibold text-white"
          :disabled="saving"
          @click="submitModal"
        >
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>
