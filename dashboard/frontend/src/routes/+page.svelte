<script lang="ts">
	/**
	 * Cluster Overview Page
	 * Shows cluster summary stats, all machines, and running models
	 */

	import { onMount } from 'svelte';
	import {
		clusterStatus,
		machines,
		runningModels,
		runningContainers
	} from '$lib/stores';
	import { wsManager } from '$lib/stores/websocket';

	// Connect to WebSocket on mount
	onMount(() => {
		wsManager.connect();
		return () => {
			// Cleanup is handled by the websocket manager
		};
	});
</script>

<div class="cluster-overview">
	<h1>LLM Serve Dashboard</h1>

	<!-- Cluster Summary Stats -->
	<section class="summary-stats">
		<h2>Cluster Summary</h2>
		<div class="stats-grid">
			<div class="stat-card">
				<div class="stat-label">Total Machines</div>
				<div class="stat-value">{$clusterStatus.total_machines}</div>
			</div>
			<div class="stat-card">
				<div class="stat-label">Online Machines</div>
				<div class="stat-value">{$clusterStatus.online_machines}</div>
			</div>
			<div class="stat-card">
				<div class="stat-label">Total GPUs</div>
				<div class="stat-value">{$clusterStatus.total_gpus}</div>
			</div>
			<div class="stat-card">
				<div class="stat-label">Free GPUs</div>
				<div class="stat-value">{$clusterStatus.free_gpus}</div>
			</div>
		</div>
	</section>

	<!-- Running Models -->
	<section class="running-models">
		<h2>Running Models</h2>
		{#if $runningModels.length > 0}
			<ul class="model-list">
				{#each $runningModels as model}
					<li class="model-item">{model}</li>
				{/each}
			</ul>
		{:else}
			<p class="empty-state">No models currently running</p>
		{/if}
	</section>

	<!-- Machines Grid -->
	<section class="machines-section">
		<h2>Machines</h2>
		{#if $machines.length > 0}
			<div class="machines-grid">
				{#each $machines as machine}
					<a href="/machine/{machine.machine_id}" class="machine-card">
						<div class="machine-header">
							<h3>{machine.hostname}</h3>
							<span class="status-badge" class:online={machine.connected}>
								{machine.connected ? 'Online' : 'Offline'}
							</span>
						</div>
						<div class="machine-stats">
							<div class="stat">
								<span class="stat-label">CPUs:</span>
								<span class="stat-value">{machine.cpu_cores}</span>
							</div>
							<div class="stat">
								<span class="stat-label">GPUs:</span>
								<span class="stat-value">{machine.gpus.length}</span>
							</div>
							<div class="stat">
								<span class="stat-label">Memory:</span>
								<span class="stat-value">{machine.memory_used_gb.toFixed(1)} / {machine.memory_total_gb.toFixed(1)} GB</span>
							</div>
							<div class="stat">
								<span class="stat-label">CPU Load:</span>
								<span class="stat-value">{machine.cpu_load_percent.toFixed(1)}%</span>
							</div>
						</div>
						{#if machine.containers.length > 0}
							<div class="machine-containers">
								<span class="container-count">{machine.containers.length} container{machine.containers.length !== 1 ? 's' : ''} running</span>
							</div>
						{/if}
					</a>
				{/each}
			</div>
		{:else}
			<p class="empty-state">No machines registered</p>
		{/if}
	</section>

	<!-- Running Containers -->
	<section class="containers-section">
		<h2>Running Containers</h2>
		{#if $runningContainers.length > 0}
			<div class="containers-list">
				{#each $runningContainers as { machine, container }}
					<div class="container-item">
						<div class="container-header">
							<span class="container-model">{container.model}</span>
							<span class="container-runtime">{container.runtime}</span>
						</div>
						<div class="container-details">
							<span class="container-machine">on {machine.hostname}</span>
							<span class="container-gpus">GPUs: {container.gpus.join(', ')}</span>
							<span class="container-status status-{container.status}">{container.status}</span>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<p class="empty-state">No containers running</p>
		{/if}
	</section>
</div>

<style>
	.cluster-overview {
		padding: 2rem;
		max-width: 1400px;
		margin: 0 auto;
	}

	h1 {
		font-size: 2rem;
		margin-bottom: 2rem;
		color: #1a1a1a;
	}

	h2 {
		font-size: 1.5rem;
		margin-bottom: 1rem;
		color: #333;
	}

	section {
		margin-bottom: 3rem;
	}

	/* Summary Stats */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.stat-card {
		background: #f8f9fa;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		padding: 1.5rem;
		text-align: center;
	}

	.stat-label {
		font-size: 0.875rem;
		color: #6c757d;
		margin-bottom: 0.5rem;
	}

	.stat-value {
		font-size: 2rem;
		font-weight: 600;
		color: #212529;
	}

	/* Running Models */
	.model-list {
		list-style: none;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.model-item {
		background: #e7f3ff;
		border: 1px solid #b3d9ff;
		border-radius: 4px;
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
		color: #004085;
	}

	/* Machines Grid */
	.machines-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1rem;
	}

	.machine-card {
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		padding: 1.5rem;
		text-decoration: none;
		color: inherit;
		transition: all 0.2s;
	}

	.machine-card:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		transform: translateY(-2px);
	}

	.machine-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.machine-header h3 {
		margin: 0;
		font-size: 1.25rem;
		color: #212529;
	}

	.status-badge {
		padding: 0.25rem 0.75rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
		background: #dc3545;
		color: white;
	}

	.status-badge.online {
		background: #28a745;
	}

	.machine-stats {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.machine-stats .stat {
		display: flex;
		justify-content: space-between;
	}

	.machine-stats .stat-label {
		color: #6c757d;
		font-size: 0.875rem;
	}

	.machine-stats .stat-value {
		font-weight: 500;
		color: #212529;
		font-size: 0.875rem;
	}

	.machine-containers {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #dee2e6;
	}

	.container-count {
		font-size: 0.875rem;
		color: #6c757d;
	}

	/* Running Containers */
	.containers-list {
		display: grid;
		gap: 1rem;
	}

	.container-item {
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		padding: 1rem;
	}

	.container-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.container-model {
		font-weight: 600;
		color: #212529;
	}

	.container-runtime {
		background: #f8f9fa;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		color: #6c757d;
	}

	.container-details {
		display: flex;
		gap: 1rem;
		font-size: 0.875rem;
		color: #6c757d;
	}

	.container-status {
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-weight: 500;
	}

	.status-running {
		background: #d4edda;
		color: #155724;
	}

	.status-starting {
		background: #fff3cd;
		color: #856404;
	}

	.status-stopped {
		background: #f8d7da;
		color: #721c24;
	}

	.status-error {
		background: #f8d7da;
		color: #721c24;
	}

	/* Empty State */
	.empty-state {
		color: #6c757d;
		font-style: italic;
		padding: 2rem;
		text-align: center;
		background: #f8f9fa;
		border-radius: 8px;
	}
</style>
