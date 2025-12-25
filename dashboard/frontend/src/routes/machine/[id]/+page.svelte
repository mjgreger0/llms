<script lang="ts">
	/**
	 * Machine Detail Page
	 * Shows detailed information about a specific machine
	 */

	import { onMount } from 'svelte';
	import { getMachine } from '$lib/stores';
	import { wsManager } from '$lib/stores/websocket';

	// Get machine ID from page data
	export let data: { id: string };

	// Subscribe to specific machine
	$: machine = getMachine(data.id);

	// Connect to WebSocket on mount
	onMount(() => {
		wsManager.connect();
		return () => {
			// Cleanup is handled by the websocket manager
		};
	});
</script>

<div class="machine-detail">
	<div class="header">
		<a href="/" class="back-link">← Back to Cluster Overview</a>
	</div>

	{#if $machine}
		<div class="machine-info">
			<div class="machine-title">
				<h1>{$machine.hostname}</h1>
				<span class="status-badge" class:online={$machine.connected}>
					{$machine.connected ? 'Online' : 'Offline'}
				</span>
			</div>

			<!-- System Stats -->
			<section class="system-stats">
				<h2>System Information</h2>
				<div class="stats-grid">
					<div class="stat-item">
						<span class="stat-label">Machine ID</span>
						<span class="stat-value">{$machine.machine_id}</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">Hostname</span>
						<span class="stat-value">{$machine.hostname}</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">CPU Model</span>
						<span class="stat-value">{$machine.cpu_model || 'N/A'}</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">CPU Cores</span>
						<span class="stat-value">{$machine.cpu_cores}</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">CPU Load</span>
						<span class="stat-value">{$machine.cpu_load_percent.toFixed(1)}%</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">Memory</span>
						<span class="stat-value">
							{$machine.memory_used_gb.toFixed(1)} / {$machine.memory_total_gb.toFixed(1)} GB
							({(($machine.memory_used_gb / $machine.memory_total_gb) * 100).toFixed(1)}%)
						</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">Memory Available</span>
						<span class="stat-value">{$machine.memory_available_gb.toFixed(1)} GB</span>
					</div>
					<div class="stat-item">
						<span class="stat-label">Last Seen</span>
						<span class="stat-value">{$machine.last_seen ? new Date($machine.last_seen).toLocaleString() : 'Never'}</span>
					</div>
				</div>
			</section>

			<!-- GPUs -->
			<section class="gpus-section">
				<h2>GPUs ({$machine.gpus.length})</h2>
				{#if $machine.gpus.length > 0}
					<div class="gpus-grid">
						{#each $machine.gpus as gpu}
							<div class="gpu-card">
								<div class="gpu-header">
									<h3>GPU {gpu.gpu_index}</h3>
									{#if gpu.assigned_model}
										<span class="gpu-status assigned">Assigned</span>
									{:else}
										<span class="gpu-status free">Free</span>
									{/if}
								</div>
								<div class="gpu-info">
									<div class="gpu-stat">
										<span class="label">Name:</span>
										<span class="value">{gpu.gpu_name}</span>
									</div>
									<div class="gpu-stat">
										<span class="label">UUID:</span>
										<span class="value uuid">{gpu.gpu_uuid}</span>
									</div>
									<div class="gpu-stat">
										<span class="label">Memory:</span>
										<span class="value">
											{gpu.memory_used_gb.toFixed(1)} / {gpu.memory_total_gb.toFixed(1)} GB
											({((gpu.memory_used_gb / gpu.memory_total_gb) * 100).toFixed(1)}%)
										</span>
									</div>
									<div class="gpu-stat">
										<span class="label">Utilization:</span>
										<span class="value">{gpu.utilization.toFixed(1)}%</span>
									</div>
									{#if gpu.temperature_c !== null}
										<div class="gpu-stat">
											<span class="label">Temperature:</span>
											<span class="value">{gpu.temperature_c}°C</span>
										</div>
									{/if}
									{#if gpu.assigned_model}
										<div class="gpu-stat">
											<span class="label">Assigned Model:</span>
											<span class="value model">{gpu.assigned_model}</span>
										</div>
									{/if}
								</div>
								<!-- Memory Usage Bar -->
								<div class="progress-bar">
									<div class="progress-fill" style="width: {(gpu.memory_used_gb / gpu.memory_total_gb) * 100}%"></div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="empty-state">No GPUs detected</p>
				{/if}
			</section>

			<!-- Running Containers -->
			<section class="containers-section">
				<h2>Running Containers ({$machine.containers.length})</h2>
				{#if $machine.containers.length > 0}
					<div class="containers-list">
						{#each $machine.containers as container}
							<div class="container-card">
								<div class="container-header">
									<h3>{container.model}</h3>
									<span class="container-status status-{container.status}">{container.status}</span>
								</div>
								<div class="container-info">
									<div class="container-stat">
										<span class="label">Container ID:</span>
										<span class="value container-id">{container.container_id}</span>
									</div>
									<div class="container-stat">
										<span class="label">Runtime:</span>
										<span class="value">{container.runtime}</span>
									</div>
									<div class="container-stat">
										<span class="label">GPUs:</span>
										<span class="value">{container.gpus.join(', ')}</span>
									</div>
									{#if container.uptime !== null}
										<div class="container-stat">
											<span class="label">Uptime:</span>
											<span class="value">{Math.floor(container.uptime / 3600)}h {Math.floor((container.uptime % 3600) / 60)}m</span>
										</div>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="empty-state">No containers running</p>
				{/if}
			</section>
		</div>
	{:else}
		<div class="loading-state">
			<p>Loading machine details...</p>
		</div>
	{/if}
</div>

<style>
	.machine-detail {
		padding: 2rem;
		max-width: 1400px;
		margin: 0 auto;
	}

	.header {
		margin-bottom: 2rem;
	}

	.back-link {
		color: #007bff;
		text-decoration: none;
		font-size: 0.875rem;
	}

	.back-link:hover {
		text-decoration: underline;
	}

	.machine-title {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 2rem;
	}

	h1 {
		font-size: 2rem;
		margin: 0;
		color: #1a1a1a;
	}

	h2 {
		font-size: 1.5rem;
		margin-bottom: 1rem;
		color: #333;
	}

	h3 {
		margin: 0;
		font-size: 1.125rem;
		color: #212529;
	}

	section {
		margin-bottom: 3rem;
	}

	.status-badge {
		padding: 0.5rem 1rem;
		border-radius: 20px;
		font-size: 0.875rem;
		font-weight: 600;
		background: #dc3545;
		color: white;
	}

	.status-badge.online {
		background: #28a745;
	}

	/* System Stats */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 1rem;
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		padding: 1.5rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.stat-label {
		font-size: 0.875rem;
		color: #6c757d;
		font-weight: 500;
	}

	.stat-value {
		font-size: 1rem;
		color: #212529;
	}

	/* GPUs */
	.gpus-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
		gap: 1rem;
	}

	.gpu-card {
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		padding: 1.5rem;
	}

	.gpu-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.gpu-status {
		padding: 0.25rem 0.75rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.gpu-status.free {
		background: #d4edda;
		color: #155724;
	}

	.gpu-status.assigned {
		background: #fff3cd;
		color: #856404;
	}

	.gpu-info {
		display: grid;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.gpu-stat, .container-stat {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
	}

	.gpu-stat .label, .container-stat .label {
		color: #6c757d;
		font-size: 0.875rem;
	}

	.gpu-stat .value, .container-stat .value {
		font-weight: 500;
		color: #212529;
		font-size: 0.875rem;
		text-align: right;
	}

	.value.uuid, .value.container-id {
		font-family: monospace;
		font-size: 0.75rem;
		word-break: break-all;
	}

	.value.model {
		font-weight: 600;
		color: #007bff;
	}

	.progress-bar {
		width: 100%;
		height: 8px;
		background: #e9ecef;
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #28a745 0%, #ffc107 70%, #dc3545 100%);
		transition: width 0.3s ease;
	}

	/* Containers */
	.containers-list {
		display: grid;
		gap: 1rem;
	}

	.container-card {
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		padding: 1.5rem;
	}

	.container-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.container-status {
		padding: 0.25rem 0.75rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
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

	.container-info {
		display: grid;
		gap: 0.75rem;
	}

	/* Empty and Loading States */
	.empty-state, .loading-state {
		color: #6c757d;
		font-style: italic;
		padding: 2rem;
		text-align: center;
		background: #f8f9fa;
		border-radius: 8px;
	}
</style>
