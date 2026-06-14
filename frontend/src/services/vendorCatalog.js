import api from './api'

export async function getVendorCatalog() {
  const { data } = await api.get('/appliances/vendor-catalog')
  return data
}

export async function saveVendorCatalog(payload) {
  const { data } = await api.put('/appliances/vendor-catalog', payload)
  return data
}
