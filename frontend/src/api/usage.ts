import type {
  AccountsResponse,
  CreateAccountRequest,
  CreateAccountResponse,
  UpdateAccountRequest,
  UpdateAccountResponse,
  UsageResponse,
} from '../types'

async function parseJson<T>(res: Response): Promise<T> {
  const body = await res.json()
  if (!res.ok) {
    const message = body?.detail || body?.message || 'Request failed'
    throw new Error(message)
  }
  return body as T
}

export async function getAccounts(): Promise<AccountsResponse> {
  const res = await fetch('/api/accounts')
  return parseJson<AccountsResponse>(res)
}

export async function getUsage(accountId: string): Promise<UsageResponse> {
  const res = await fetch(`/api/usage?accountId=${encodeURIComponent(accountId)}`)
  return parseJson<UsageResponse>(res)
}

export async function createAccount(payload: CreateAccountRequest): Promise<CreateAccountResponse> {
  const res = await fetch('/api/accounts', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return parseJson<CreateAccountResponse>(res)
}

export async function updateAccount(accountId: string, payload: UpdateAccountRequest): Promise<UpdateAccountResponse> {
  const res = await fetch(`/api/accounts/${encodeURIComponent(accountId)}`, {
    method: 'PUT',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return parseJson<UpdateAccountResponse>(res)
}
