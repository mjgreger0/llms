<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { wsManager } from '$lib/stores';
	import Navigation from '$lib/components/Navigation.svelte';
	import Header from '$lib/components/Header.svelte';
	import '../app.css';

	let sidebarOpen = true;
	let isMobile = false;

	// Page title mapping
	const pageTitles: { [key: string]: string } = {
		'/': 'Cluster Overview',
		'/chat': 'Chat/Test',
		'/logs': 'Logs'
	};

	$: pageTitle = pageTitles[$page.url.pathname] || 'Dashboard';

	// Connect to WebSocket on mount
	onMount(() => {
		wsManager.connect();

		// Check if mobile on mount and resize
		checkMobile();
		window.addEventListener('resize', checkMobile);

		return () => {
			window.removeEventListener('resize', checkMobile);
		};
	});

	onDestroy(() => {
		wsManager.disconnect();
	});

	function checkMobile() {
		isMobile = window.innerWidth < 768;
		// Auto-collapse sidebar on mobile
		if (isMobile) {
			sidebarOpen = false;
		} else {
			sidebarOpen = true;
		}
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function closeSidebarOnMobile() {
		if (isMobile) {
			sidebarOpen = false;
		}
	}
</script>

<div class="app-layout">
	<!-- Mobile menu toggle button -->
	{#if isMobile}
		<button class="mobile-menu-toggle" on:click={toggleSidebar} aria-label="Toggle menu">
			<span class="hamburger-icon">☰</span>
		</button>
	{/if}

	<!-- Sidebar -->
	<aside class="sidebar" class:open={sidebarOpen}>
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div class="sidebar-content" on:click={closeSidebarOnMobile}>
			<Navigation />
		</div>
	</aside>

	<!-- Mobile overlay -->
	{#if isMobile && sidebarOpen}
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div class="overlay" on:click={toggleSidebar}></div>
	{/if}

	<!-- Main content area -->
	<div class="main-container">
		<Header title={pageTitle} />
		<main class="main-content">
			<slot />
		</main>
	</div>
</div>

<style>
	.app-layout {
		display: grid;
		grid-template-columns: var(--sidebar-width) 1fr;
		grid-template-rows: 1fr;
		height: 100vh;
		width: 100%;
		overflow: hidden;
	}

	.sidebar {
		grid-column: 1;
		grid-row: 1;
		height: 100vh;
		overflow-y: auto;
		transition: transform var(--transition-normal);
	}

	.sidebar-content {
		height: 100%;
	}

	.main-container {
		grid-column: 2;
		grid-row: 1;
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.main-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-6);
		background-color: var(--color-bg);
	}

	.mobile-menu-toggle {
		display: none;
	}

	.overlay {
		display: none;
	}

	/* Mobile responsiveness */
	@media (max-width: 768px) {
		.app-layout {
			grid-template-columns: 1fr;
		}

		.sidebar {
			position: fixed;
			top: 0;
			left: 0;
			bottom: 0;
			z-index: 1000;
			width: var(--sidebar-width);
			transform: translateX(-100%);
			box-shadow: var(--shadow-lg);
		}

		.sidebar.open {
			transform: translateX(0);
		}

		.main-container {
			grid-column: 1;
		}

		.mobile-menu-toggle {
			display: flex;
			align-items: center;
			justify-content: center;
			position: fixed;
			top: var(--space-3);
			left: var(--space-3);
			z-index: 999;
			width: 40px;
			height: 40px;
			background-color: var(--color-bg-secondary);
			border: 1px solid var(--color-border);
			border-radius: var(--radius-md);
			cursor: pointer;
			transition: all var(--transition-fast);
		}

		.mobile-menu-toggle:hover {
			background-color: var(--color-bg-hover);
		}

		.hamburger-icon {
			font-size: var(--font-size-xl);
			color: var(--color-text);
		}

		.overlay {
			display: block;
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			background-color: rgba(0, 0, 0, 0.5);
			z-index: 999;
		}

		.main-content {
			padding: var(--space-4);
			padding-top: calc(var(--space-4) + 48px); /* Account for mobile menu button */
		}
	}

	/* Tablet adjustments */
	@media (max-width: 900px) and (min-width: 769px) {
		.main-content {
			padding: var(--space-5);
		}
	}

	/* Small mobile adjustments */
	@media (max-width: 480px) {
		.main-content {
			padding: var(--space-3);
			padding-top: calc(var(--space-3) + 48px);
		}
	}
</style>
