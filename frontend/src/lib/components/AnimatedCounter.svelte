<script lang="ts">
import { onMount } from "svelte";

let {
    value,
    duration = 1200,
    label = "",
    color = "",
}: {
    value: number | string; // Handle potential string types from DB
    duration?: number;
    label?: string;
    color?: string;
} = $props();

let displayValue = $state(0);
let containerEl: HTMLDivElement | null = $state(null);
let hasEnteredView = $state(false);
let rafId: number;

const textColor = $derived(
    color === "gold" ? "text-gold" : 
    color === "success" ? "text-success" : 
    color === "accent" ? "text-accent" : 
    "text-white"
);

// 1. Handle Visibility (Intersection Observer)
onMount(() => {
    if (!containerEl) return;
    const io = new IntersectionObserver(
        ([entry]) => {
            if (entry.isIntersecting) {
                hasEnteredView = true;
                // We don't disconnect so it can re-trigger if needed, 
                // but usually for dashboards, once is enough.
                io.disconnect();
            }
        },
        { threshold: 0.1 }
    );
    io.observe(containerEl);
    return () => {
        io.disconnect();
        cancelAnimationFrame(rafId);
    };
});

// 2. React to value changes or entering view
$effect(() => {
    // We only animate if the component is in view
    if (hasEnteredView) {
        // Ensure value is a number (handles the "string from DB" issue)
        const numericValue = Number(value) || 0;
        animate(numericValue);
    }
});

function animate(target: number) {
    cancelAnimationFrame(rafId); // Stop any currently running animation
    
    const startValue = displayValue;
    const startTime = performance.now();

    const step = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        
        // Animate from the current displayValue to the new target
        displayValue = Math.round(startValue + (target - startValue) * eased);

        if (progress < 1) {
            rafId = requestAnimationFrame(step);
        }
    };
    
    rafId = requestAnimationFrame(step);
}
</script>

<div bind:this={containerEl} class="flex flex-col items-center">
    <span class="text-3xl md:text-4xl font-bold tabular-nums {textColor}">
        {displayValue.toLocaleString()}
    </span>
    {#if label}
        <span class="text-xs text-[#8888a0] font-medium mt-1 uppercase tracking-wider">
            {label}
        </span>
    {/if}
</div>