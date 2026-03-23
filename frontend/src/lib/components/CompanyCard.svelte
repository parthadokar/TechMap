<script>
  import { createEventDispatcher } from 'svelte';
  export let company;
  export let selected = false;

  const dispatch = createEventDispatcher();

  const TYPE_META = {
    software:  { label: 'Software / Dev',    bg: 'bg-blue-100',   text: 'text-blue-700'   },
    itsupport: { label: 'IT Support / MSP',  bg: 'bg-green-100',  text: 'text-green-700'  },
    cloud:     { label: 'Cloud / SaaS',      bg: 'bg-purple-100', text: 'text-purple-700' },
    unknown:   { label: 'Unknown',           bg: 'bg-gray-100',   text: 'text-gray-600'   },
  };

  $: meta = TYPE_META[company.type] ?? TYPE_META.unknown;
</script>

<div
  class="p-3 border-b cursor-pointer transition-colors duration-150
         {selected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50 border-l-4 border-l-transparent'}"
  on:click
  on:keydown={(e) => e.key === 'Enter' && dispatch('click')}
  role="button"
  tabindex="0"
>
  <div class="flex items-start justify-between gap-2">
    <p class="text-sm font-semibold text-gray-900 leading-tight">{company.name}</p>
    <span class="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full {meta.bg} {meta.text}">
      {meta.label}
    </span>
  </div>

  {#if company.address}
    <p class="text-xs text-gray-500 mt-0.5 truncate">{company.address}</p>
  {/if}

  <div class="flex items-center gap-3 mt-1.5 flex-wrap">
    {#if company.phone}
      <a
        href="tel:{company.phone}"
        class="text-xs text-gray-600 hover:text-gray-900"
        on:click|stopPropagation
      >
        {company.phone}
      </a>
    {/if}

    {#if company.website}
      <a
        href={company.website}
        target="_blank"
        rel="noopener noreferrer"
        class="text-xs text-blue-600 hover:underline truncate max-w-[160px]"
        on:click|stopPropagation
      >
        {company.website.replace(/^https?:\/\//, '')}
      </a>
    {/if}
  </div>
</div>
