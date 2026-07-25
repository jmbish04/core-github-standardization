// import { ConfigManager } from "@/lib/config";
// import { isUuid } from "@/utils/common";
// import { Logger } from "@/lib/logger";


/**
 * Generic helper to fetch a secret value.
 * 
 * Precedence:
 * 1. KV Config (Metadata/Pointer) -> Secret Store (Value)
 * 2. Secrets Store (Direct Binding fallback)
 * 3. Environment Variable (Legacy/Local)
 * 
 * CAUTION: This should ONLY be used for operations where the worker is retrieving a secret
 * from the secret-store in order to set the value inside of a GitHub repo, or other external provisioning.
 * 
 * For standard Worker operations (using the key itself), use `env.{SECRET_BINDING_NAME}.get()` directly.
 */
export async function getSecret(env: Env, key: string): Promise<string | undefined> {
    const logger = new Logger(env, 'utils/secrets');

    // 1. Try KV Config (Pointer Pattern)
    try {
        const manager = new ConfigManager(env.KV_CONFIGS);
        const metadata = await manager.getMetadata(key); 

        // CASE A: The key exists in KV and is managed by Secret Store
        if (metadata?.isSecretStoreManaged && metadata.secretName) {
            // We fetch the ACTUAL value from Cloudflare's Secret Store API
            try {
                 const { getSecretsStoreClient } = await import("@/utils/cloudflare/secret-store");
                 const client = await getSecretsStoreClient(env);
                 
                 // We need a store ID. We assume the first available store for now.
                 const store = await client.getDefaultStore();
                 
                 // If we have the ID in metadata.value, use it.
                 // Otherwise, try to find by name.
                 let secretId = String(metadata.value);
                 
                 // If value looks like a UUID, use it. If not (legacy or error), find by name.
                 if (!isUuid(secretId)) {
                     const found = await client.getSecretByName(store.id, metadata.secretName);
                     if (found) secretId = found.id;
                 }
                 
                 if (secretId) {
                    return await client.getSecretValue(store.id, secretId);
                 }
            } catch (apiError: any) {
                logger.warn(`[getSecret] Cloudflare Config Store API check failed for ${key}`, { error: apiError.message });
                // Fallthrough to fallback
            }
        }

        // CASE B: The key exists in KV as a plain string (Non-sensitive config)
        if (metadata?.value && !metadata.isSecretStoreManaged) {
            return String(metadata.value);
        }
        
    } catch (e: any) {
        // KV lookup failed or API failed
        // We log as warning because we have fallbacks
        logger.warn(`[getSecret] KV/API lookup failed for ${key}`, { error: e.message });
    }

    // 2. Fallback: Check Secrets Store or Env Var Binding (Legacy behavior compliance)
    const envVal = (env as any)[key];
    if (envVal && typeof envVal?.get === 'function') {
        const val = await envVal.get();
        // logger.debug(`[getSecret] Retrieved ${key} from direct binding`); // verbose
        return val;
    }
    
    // 3. Fallback: Direct property
    return envVal;
}

export async function getWorkerApiKey(env: Env): Promise<string | undefined> {
    if (env.WORKER_API_KEY) {
        return typeof env.WORKER_API_KEY === 'string' 
            ? env.WORKER_API_KEY 
            : await (env.WORKER_API_KEY as any).get();
    }
    return getSecret(env, "WORKER_API_KEY");
}


export async function getGeminiApiKey(env: Env): Promise<string | undefined> {
    if (env.GEMINI_API_KEY) {
        return typeof env.GEMINI_API_KEY === 'string'
            ? env.GEMINI_API_KEY
            : await (env.GEMINI_API_KEY as any).get();
    }
    return getSecret(env, "GEMINI_API_KEY");
}

export async function getCloudflareApiToken(env: Env): Promise<string | undefined> {
    if (env.CLOUDFLARE_API_TOKEN) {
        return typeof env.CLOUDFLARE_API_TOKEN === 'string'
            ? env.CLOUDFLARE_API_TOKEN
            : await (env.CLOUDFLARE_API_TOKEN as any).get();
    }
    return getSecret(env, "CLOUDFLARE_API_TOKEN");
}

export async function getCloudflareAccountId(env: Env): Promise<string | undefined> {
    if (env.CLOUDFLARE_ACCOUNT_ID) {
        return typeof env.CLOUDFLARE_ACCOUNT_ID === 'string'
            ? env.CLOUDFLARE_ACCOUNT_ID
            : await (env.CLOUDFLARE_ACCOUNT_ID as any).get();
    }
    return getSecret(env, "CLOUDFLARE_ACCOUNT_ID");
}

