export type UsageItem = {
  name: string
  used: number
  limit: number
  percent: number
}

export type UsageResponse = {
  data: {
    monthUsage: {
      percent: number
      items: UsageItem[]
      monthPlan: UsageItem
    }
    usage: {
      percent: number
      items: UsageItem[]
      plan: UsageItem
      compensation: UsageItem
    }
  }
}

export type Account = {
  id: string
  name: string
}

export type AccountsResponse = {
  data: Account[]
}

export type CreateAccountRequest = {
  name: string
  cookie: string
  referer?: string
  timezone?: string
  userAgent?: string
}

export type CreateAccountResponse = {
  data: Account
}

export type UpdateAccountRequest = {
  name: string
  cookie: string
  referer?: string
  timezone?: string
  userAgent?: string
}

export type UpdateAccountResponse = {
  data: Account
}
