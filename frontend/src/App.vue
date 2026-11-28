<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">会展布展协作平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">策展人、设计师和施工团队共同编排展位布局、展品运输与搭建进度，按同一版执行方案完成布展交付。</span>
        <span class="head-user">当前值班：应用开发组</span>
      </header>
      <RouterView :key="$route.path" />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "场馆规划", path: "/venue" }, { label: "展位编排", path: "/booth" }, { label: "参展商管理", path: "/exhibitor" }, { label: "方案设计", path: "/design" }, { label: "搭建物料", path: "/material" }, { label: "展品运输", path: "/transport" }, { label: "搭建进度", path: "/construction" }, { label: "用电配置", path: "/electrical" }, { label: "安全巡检", path: "/safety" }, { label: "灯光编排", path: "/lighting" }, { label: "影音布置", path: "/audio_visual" }, { label: "家具配置", path: "/furniture" }, { label: "导视系统", path: "/signage" }, { label: "验收清单", path: "/checklist" }, { label: "变更指令", path: "/change_order" }, { label: "布展排期", path: "/schedule" }, { label: "交场确认", path: "/handover" }, { label: "突发事件", path: "/incident" }, { label: "事故临时导视", path: "/emergency_signage" }, { label: "应急通行面板", path: "/emergency" }]
</script>
