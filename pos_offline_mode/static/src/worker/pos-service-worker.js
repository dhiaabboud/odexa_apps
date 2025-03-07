importScripts('/pos_retail_offline/static/src/apps/idb-keyval.js');
importScripts('/pos_retail_offline/static/src/apps/PosIDB.js');



const serializeRequest = async (req) => ({
    url: req.url,
    body: await req.json(),
});

const serializeResponse = async (res) => ({
    body: await res.text(),
    status: res.status,
    statusText: res.statusText,
    headers: Object.fromEntries(res.headers.entries()),
});

const deserializeResponse = (responseData) => {
    const {body} = responseData;
    delete responseData.body;
    return new Response(body, responseData);
};

const buildCacheKey = ({url, body: {method, params}}) =>
    JSON.stringify({
        url,
        method,
        params,
    });

const isGET = (request) => request.method === 'GET';

const cacheTheRequest = async (request, response) => {
    if (isGET(request)) {
        const cache = await caches.open('POS-ASSETS');
        await cache.put(request.clone(), response.clone());
    } else {
        let stopCaching = await PosIDB.get('stopCaching')
        if (stopCaching) {
            console.warn('>>> system stopCaching !!!  return true')
            return true
        } else {
            const serializedRequest = await serializeRequest(request.clone());
            const serializedResponse = await serializeResponse(response.clone());
            const requestStr = buildCacheKey(serializedRequest)
            console.warn('>>> started saving cache')
            console.log(requestStr)
            console.log(serializedResponse)
            await PosIDB.set(requestStr, serializedResponse);
        }
    }
};

const getResponseFromCache = async (request) => {
    if (isGET(request)) {
        const cache = await caches.open('POS-ASSETS');
        return await cache.match(request);
    } else {
        const serializedRequest = await serializeRequest(request);
        const cachedResponse = await PosIDB.get(buildCacheKey(serializedRequest));
        if (cachedResponse) {
            return deserializeResponse(cachedResponse);
        } else {
            throw new Error(`Unable to find ${request.url} from (idb) cache.`);
        }
    }
};

const processFetchEvent = async ({request}) => {
    try {
        const response = await fetch(request.clone());
        await cacheTheRequest(request, response.clone());
        return response;
    } catch (fetchError) {
        try {
            console.log('[Internet or Odoo Server] offline mode. Swith to getResponseFromCache ')
            let cache = await getResponseFromCache(request);
            if (!cache) {
                console.error(request.url + ' not found in cache')
            }
            return cache
        } catch (err) {
            console.warn('An error occured when reading the request from cache.', err);
        }
    }
};

self.addEventListener('fetch', (event) => event.respondWith(processFetchEvent(event)));