<script setup lang="ts">
import { ref } from 'vue';
import AgentWorkflowTab from './components/AgentWorkflowTab.vue';
import DashboardTab from './components/DashboardTab.vue';
import DualColumnProposalsTab from './components/DualColumnProposalsTab.vue';
import EvidenceDrawer from './components/EvidenceDrawer.vue';
import FinancialVetoTab from './components/FinancialVetoTab.vue';
import Header from './components/Header.vue';
import VocClusterTab from './components/VocClusterTab.vue';
import {
  INITIAL_TASKS,
  MOCK_CLUSTERS,
  MOCK_PACKAGING_PROPOSALS,
  MOCK_PHYSICAL_PROPOSALS,
  MOCK_VISUAL_EVIDENCES,
} from './mock/data';
import type { InsightTask, Marketplace, PainPointCluster } from './types';

type TabType = 'dashboard' | 'agent' | 'voc' | 'proposals' | 'financial';

const activeTab = ref<TabType>('dashboard');
const selectedMarketplace = ref<Marketplace>('US');
const tasks = ref<InsightTask[]>(INITIAL_TASKS);
const currentTask = ref<InsightTask>(tasks.value[0]);

// Evidence drawer state
const isDrawerOpen = ref(false);
const drawerTitle = ref('3D扶手按键卡扣脆断');
const drawerCount = ref(42);

// Notification toast state
const toastMessage = ref<string | null>(null);

const showToast = (msg: string) => {
  toastMessage.value = msg;
  setTimeout(() => {
    toastMessage.value = null;
  }, 3200);
};

const handleSelectTask = (taskId: string) => {
  const found = tasks.value.find(t => t.id === taskId);
  if (found) {
    currentTask.value = found;
    selectedMarketplace.value = found.marketplace;
    showToast(`已切换至任务: ${found.asin} (${found.productTitle.slice(0, 20)}...)`);
  }
};

const handleSelectAsin = (asin: string) => {
  const found = tasks.value.find(t => t.asin === asin);
  if (found) {
    currentTask.value = found;
    selectedMarketplace.value = found.marketplace;
    showToast(`已加载商品: ${asin}`);
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
  showToast('✓ 工程改款 RFC 规格表导出成功 (PDF & Excel 格式打包已就绪)');
};
</script>

<template>
  <div class="min-h-screen bg-[#090a0f] text-zinc-100 selection:bg-cyan-500/30 selection:text-cyan-200">
    <!-- Ambient Background Lighting Mesh -->
    <div class="fixed inset-0 pointer-events-none overflow-hidden z-0">
      <div class="absolute -top-40 left-1/4 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[140px]" />
      <div class="absolute top-1/3 -right-40 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[140px]" />
      <div class="absolute -bottom-40 left-1/3 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[140px]" />
    </div>

    <!-- Header & Navigation -->
    <Header
      :active-tab="activeTab"
      :selected-marketplace="selectedMarketplace"
      :selected-asin="currentTask.asin"
      :is-agent-running="currentTask.status === 'running'"
      @update:active-tab="activeTab = $event"
      @update:selected-marketplace="selectedMarketplace = $event"
      @select-asin="handleSelectAsin"
    />

    <!-- Main Workspace Container -->
    <main class="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Transition for Tab Switching -->
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

    <!-- Toast Notification Banner -->
    <transition name="toast">
      <div
        v-if="toastMessage"
        class="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-zinc-900/95 border border-cyan-500/50 shadow-[0_10px_30px_rgba(0,0,0,0.8)] text-xs font-mono text-cyan-300 flex items-center gap-2 backdrop-blur-md"
      >
        <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
        <span>{{ toastMessage }}</span>
      </div>
    </transition>

    <!-- Footer -->
    <footer class="relative z-10 border-t border-zinc-900 py-6 mt-12 text-center text-xs font-mono text-zinc-500">
      <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
        <span>InsightX · Cross-Border AI Market-Insight & Dynamic Decision System</span>
        <span>Vue 3.5 + Vite 8 + TailwindCSS 4 + LangGraph Agent</span>
      </div>
    </footer>
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
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}
</style>
