<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AgentWorkflowTab from './components/AgentWorkflowTab.vue';
import AuthModal from './components/AuthModal.vue';
import DashboardTab from './components/DashboardTab.vue';
import DualColumnProposalsTab from './components/DualColumnProposalsTab.vue';
import EvidenceDrawer from './components/EvidenceDrawer.vue';
import FinancialVetoTab from './components/FinancialVetoTab.vue';
import Header from './components/Header.vue';
import IntroShowcase from './components/IntroShowcase.vue';
import VocClusterTab from './components/VocClusterTab.vue';
import {
  INITIAL_TASKS,
  MOCK_CLUSTERS,
  MOCK_PACKAGING_PROPOSALS,
  MOCK_PHYSICAL_PROPOSALS,
  MOCK_VISUAL_EVIDENCES,
} from './mock/data';
import type { AuthUser, InsightTask, Marketplace, PainPointCluster } from './types';

type TabType = 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial';

const activeTab = ref<TabType>('dashboard');
const selectedMarketplace = ref<Marketplace>('US');
const tasks = ref<InsightTask[]>(INITIAL_TASKS);
const currentTask = ref<InsightTask>(tasks.value[0]);

// Intro showcase & Auth states
const showIntro = ref(true);
const isAuthOpen = ref(false);
const currentUser = ref<AuthUser | null>(null);

const isDrawerOpen = ref(false);
const drawerTitle = ref('3D扶手按键卡扣脆断');
const drawerCount = ref(42);
const toastMessage = ref<string | null>(null);

const showToast = (msg: string) => {
  toastMessage.value = msg;
  setTimeout(() => {
    toastMessage.value = null;
  }, 2800);
};

const handleSelectTask = (taskId: string) => {
  const found = tasks.value.find(t => t.id === taskId);
  if (found) {
    currentTask.value = found;
    selectedMarketplace.value = found.marketplace;
    showToast(`已切换至: ${found.asin}`);
  }
};

const handleSelectAsin = (asin: string) => {
  const found = tasks.value.find(t => t.asin === asin);
  if (found) {
    currentTask.value = found;
    selectedMarketplace.value = found.marketplace;
    showToast(`已载入: ${asin}`);
  }
};

const handleTaskUpdated = (updated: InsightTask) => {
  currentTask.value = updated;
  const idx = tasks.value.findIndex(t => t.id === updated.id);
  if (idx !== -1) {
    tasks.value[idx] = updated;
  }
};

const handleViewClusterEvidence = (cluster: PainPointCluster) => {
  drawerTitle.value = cluster.name;
  drawerCount.value = cluster.frequency;
  isDrawerOpen.value = true;
};

const handleViewProposalEvidence = (target: { title: string; count: number }) => {
  drawerTitle.value = target.title;
  drawerCount.value = target.count;
  isDrawerOpen.value = true;
};

const handleExportRfc = () => {
  showToast('✓ 工程改款 RFC 已生成并导出');
};

const handleLoginSuccess = (user: AuthUser) => {
  currentUser.value = user;
  showToast(`✓ 欢迎回来，${user.name} (${user.roleName})`);
};

const handleLogout = () => {
  currentUser.value = null;
  localStorage.removeItem('insightx_user');
  localStorage.removeItem('insightx_token');
  showToast('已安全退出登录');
};

onMounted(() => {
  const savedUserStr = localStorage.getItem('insightx_user');
  if (savedUserStr) {
    try {
      currentUser.value = JSON.parse(savedUserStr);
    } catch {
      // ignore
    }
  }
});
</script>

<template>
  <div class="min-h-screen bg-[#08090a] text-[#f7f8f8]">
    <!-- GSAP Cinematic Product Intro Showcase Overlay -->
    <transition name="fade">
      <IntroShowcase
        v-if="showIntro"
        @enter="showIntro = false"
        @open-auth="isAuthOpen = true"
      />
    </transition>

    <!-- Main Workspace Application -->
    <div v-show="!showIntro" class="flex flex-col min-h-screen">
      <!-- Header -->
      <Header
        :active-tab="activeTab"
        :selected-marketplace="selectedMarketplace"
        :selected-asin="currentTask.asin"
        :is-agent-running="currentTask.status === 'running'"
        :current-user="currentUser"
        @update:active-tab="activeTab = $event"
        @update:selected-marketplace="selectedMarketplace = $event"
        @select-asin="handleSelectAsin"
        @open-auth="isAuthOpen = true"
        @open-intro="showIntro = true"
        @logout="handleLogout"
      />

      <!-- Main Workspace Container -->
      <main class="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full">
        <transition name="fade" mode="out-in">
          <div :key="activeTab">
            <DashboardTab
              v-if="activeTab === 'dashboard'"
              :current-task="currentTask"
              :all-tasks="tasks"
              :clusters="MOCK_CLUSTERS"
              @navigate="activeTab = $event"
              @select-task="handleSelectTask"
              @start-new-task="activeTab = 'agent'"
            />

            <AgentWorkflowTab
              v-else-if="activeTab === 'agent'"
              :current-task="currentTask"
              @task-updated="handleTaskUpdated"
            />

            <VocClusterTab
              v-else-if="activeTab === 'voc'"
              :clusters="MOCK_CLUSTERS"
              :evidences="MOCK_VISUAL_EVIDENCES"
              @view-cluster-evidence="handleViewClusterEvidence"
            />

            <DualColumnProposalsTab
              v-else-if="activeTab === 'proposals'"
              :physical-proposals="MOCK_PHYSICAL_PROPOSALS"
              :packaging-proposals="MOCK_PACKAGING_PROPOSALS"
              @view-evidence="handleViewProposalEvidence"
              @export-rfc="handleExportRfc"
            />

            <FinancialVetoTab
              v-else-if="activeTab === 'financial'"
            />
          </div>
        </transition>
      </main>

      <!-- Slide-in Evidence Drawer -->
      <EvidenceDrawer
        :is-open="isDrawerOpen"
        :target-title="drawerTitle"
        :evidence-count="drawerCount"
        @close="isDrawerOpen = false"
      />

      <!-- Auth Modal (Login / Register) -->
      <AuthModal
        :is-open="isAuthOpen"
        @close="isAuthOpen = false"
        @login-success="handleLoginSuccess"
      />

      <!-- Toast Notification -->
      <transition name="toast">
        <div
          v-if="toastMessage"
          class="fixed bottom-6 right-6 z-50 px-3.5 py-2 rounded-lg bg-[#191a1b] border border-[rgba(255,255,255,0.12)] text-xs font-mono text-[#f7f8f8] shadow-lg"
        >
          {{ toastMessage }}
        </div>
      </transition>

      <!-- Quiet Footer -->
      <footer class="border-t border-[rgba(255,255,255,0.06)] py-6 text-center text-xs font-mono text-[#5e626e]">
        <div class="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>InsightX · Cross-Border AI Market-Insight & Dynamic Decision Engine</span>
          <span>Vue 3.5 · Vite 8 · GSAP 3 · Tailwind CSS · LangGraph</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
