<script setup lang="ts">
import {
  Lock,
  Mail,
  User,
  X,
} from 'lucide-vue-next';
import { ref } from 'vue';
import type { AuthUser } from '../types';

defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'loginSuccess', user: AuthUser): void;
}>();

const mode = ref<'login' | 'register'>('login');
const email = ref('');
const password = ref('');
const name = ref('');
const role = ref<'owner' | 'pm' | 'supply_chain'>('owner');
const isLoading = ref(false);

const presetAccounts: { email: string; name: string; role: 'owner' | 'pm' | 'supply_chain'; roleName: string; desc: string }[] = [
  {
    email: 'boss@insightx.ai',
    name: '陈总 (Founder & GM)',
    role: 'owner',
    roleName: '工贸企业老板 / 决策者',
    desc: '拥有开模资金拨付、重大立项审批与财务熔断否决权限',
  },
  {
    email: 'pm@insightx.ai',
    name: '林工 (Hardware Lead)',
    role: 'pm',
    roleName: '硬件与模具产品经理',
    desc: '负责双栏改款清单定义、VLM 实拍缺陷分析与工厂图纸提需',
  },
  {
    email: 'supply@insightx.ai',
    name: '张总监 (Supply Chain)',
    role: 'supply_chain',
    roleName: '跨境供应链与运营总监',
    desc: '主导外箱尺寸降阶 (Tier Down)、FBA 履约测算与头程物流降本',
  },
];

const selectPreset = (preset: typeof presetAccounts[0]) => {
  email.value = preset.email;
  password.value = 'insightx2026';
  name.value = preset.name;
  role.value = preset.role;
  handleMockSubmit(preset);
};

const handleMockSubmit = (presetData?: typeof presetAccounts[0]) => {
  isLoading.value = true;
  setTimeout(() => {
    isLoading.value = false;
    const userRole = presetData ? presetData.role : role.value;
    const userRoleName = presetData
      ? presetData.roleName
      : userRole === 'owner'
        ? '企业决策者'
        : userRole === 'pm'
          ? '产品经理'
          : '供应链总监';

    const mockUser: AuthUser = {
      id: `USR-${Date.now()}`,
      name: presetData ? presetData.name : name.value || email.value.split('@')[0] || 'Demo User',
      email: presetData ? presetData.email : email.value || 'demo@insightx.ai',
      role: userRole,
      roleName: userRoleName,
      avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80',
    };

    localStorage.setItem('insightx_user', JSON.stringify(mockUser));
    localStorage.setItem('insightx_token', `jwt_mock_${Date.now()}`);
    emit('loginSuccess', mockUser);
    emit('close');
  }, 400);
};
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <!-- Modal Card -->
    <div class="ln-surface max-w-md w-full bg-[#0d0e11] border border-[rgba(255,255,255,0.12)] p-6 rounded-2xl shadow-2xl space-y-6 relative overflow-hidden">
      <!-- Close Button -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 p-1 text-[#8a8f98] hover:text-[#f7f8f8] transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Header & Tab Toggle -->
      <div class="space-y-2">
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold tracking-tight text-[#f7f8f8]">InsightX Account</span>
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[rgba(255,255,255,0.06)] text-[#8a8f98]">
            Mock Auth
          </span>
        </div>

        <div class="flex items-center bg-[rgba(255,255,255,0.04)] p-0.5 rounded-lg border border-[rgba(255,255,255,0.06)]">
          <button
            @click="mode = 'login'"
            :class="[
              'flex-1 py-1 text-xs font-medium rounded-md transition-colors',
              mode === 'login'
                ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]'
                : 'text-[#8a8f98] hover:text-[#f7f8f8]'
            ]"
          >
            登录账号
          </button>
          <button
            @click="mode = 'register'"
            :class="[
              'flex-1 py-1 text-xs font-medium rounded-md transition-colors',
              mode === 'register'
                ? 'bg-[rgba(255,255,255,0.1)] text-[#f7f8f8]'
                : 'text-[#8a8f98] hover:text-[#f7f8f8]'
            ]"
          >
            新用户注册
          </button>
        </div>
      </div>

      <!-- Quick 1-Click Mock Role Presets -->
      <div class="space-y-2">
        <span class="text-[11px] font-mono text-[#8a8f98] block">一键免密快速登录出海角色：</span>
        <div class="space-y-1.5">
          <button
            v-for="preset in presetAccounts"
            :key="preset.email"
            @click="selectPreset(preset)"
            class="w-full text-left p-2.5 rounded-lg bg-[rgba(255,255,255,0.02)] hover:bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.14)] transition-all flex items-center justify-between group"
          >
            <div class="space-y-0.5">
              <div class="text-xs font-medium text-[#f7f8f8] group-hover:text-[#7170ff] transition-colors flex items-center gap-1.5">
                <span>{{ preset.name }}</span>
                <span class="text-[10px] font-mono text-[#8a8f98]">({{ preset.roleName }})</span>
              </div>
              <div class="text-[10px] text-[#5e626e] line-clamp-1">
                {{ preset.desc }}
              </div>
            </div>
            <span class="text-[11px] font-mono text-[#7170ff] opacity-0 group-hover:opacity-100 transition-opacity">
              进入 →
            </span>
          </button>
        </div>
      </div>

      <!-- Divider -->
      <div class="flex items-center gap-3 text-[10px] font-mono text-zinc-600">
        <span class="flex-1 h-px bg-[rgba(255,255,255,0.06)]" />
        <span>或输入凭证</span>
        <span class="flex-1 h-px bg-[rgba(255,255,255,0.06)]" />
      </div>

      <!-- Standard Form -->
      <form @submit.prevent="handleMockSubmit()" class="space-y-3">
        <div v-if="mode === 'register'" class="space-y-1">
          <label class="text-[11px] font-mono text-[#8a8f98]">姓名 / 称呼</label>
          <div class="relative flex items-center">
            <User class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 pointer-events-none" />
            <input
              v-model="name"
              type="text"
              required
              class="w-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#f7f8f8] focus:outline-none focus:border-[rgba(255,255,255,0.2)]"
              placeholder="例如：Alex Chen"
            />
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-[11px] font-mono text-[#8a8f98]">企业工作邮箱</label>
          <div class="relative flex items-center">
            <Mail class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 pointer-events-none" />
            <input
              v-model="email"
              type="email"
              required
              class="w-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] rounded-md pl-8 pr-3 py-1.5 text-xs font-mono text-[#f7f8f8] focus:outline-none focus:border-[rgba(255,255,255,0.2)]"
              placeholder="name@company.com"
            />
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-[11px] font-mono text-[#8a8f98]">密码</label>
          <div class="relative flex items-center">
            <Lock class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 pointer-events-none" />
            <input
              v-model="password"
              type="password"
              required
              class="w-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] rounded-md pl-8 pr-3 py-1.5 text-xs font-mono text-[#f7f8f8] focus:outline-none focus:border-[rgba(255,255,255,0.2)]"
              placeholder="••••••••"
            />
          </div>
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full py-2 ln-btn-primary flex items-center justify-center gap-1.5 text-xs font-medium mt-2"
        >
          <span v-if="isLoading" class="animate-spin">⏳</span>
          <span v-else>{{ mode === 'login' ? '立即登录' : '创建账号' }}</span>
        </button>
      </form>
    </div>
  </div>
</template>
