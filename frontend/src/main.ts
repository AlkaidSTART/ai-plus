import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { installProviders } from './app/providers'
import { router } from './app/router'

const app = createApp(App)

installProviders(app)
app.use(router)

app.mount('#app')
