import { serverClient } from './supabase'
import { SmugMugClient } from './smugmug'

export interface StoredTokens {
  access_token:        string
  access_token_secret: string
  smugmug_user:        string
}

/** Read stored OAuth tokens from DB. Throws if not connected. */
export async function getStoredTokens(): Promise<StoredTokens> {
  const { data, error } = await serverClient()
    .from('oauth_tokens')
    .select('access_token, access_token_secret, smugmug_user')
    .eq('id', 1)
    .single()

  if (error || !data) throw new Error('Not connected to SmugMug')
  return data as StoredTokens
}

/** Build a SmugMugClient from stored tokens. Throws if not connected. */
export async function getSmugMugClient(): Promise<[SmugMugClient, string]> {
  const tokens = await getStoredTokens()
  const client = new SmugMugClient(
    process.env.SMUGMUG_API_KEY!,
    process.env.SMUGMUG_API_SECRET!,
    tokens.access_token,
    tokens.access_token_secret
  )
  return [client, tokens.smugmug_user]
}
