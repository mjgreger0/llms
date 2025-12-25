<script lang="ts">
	/**
	 * Chat/Test Interface Page
	 * Interactive chat interface for testing LLM models
	 */

	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { streamChatCompletion } from '$lib/api/streaming';
	import type { ChatMessage } from '$lib/api/types';

	// State
	let availableModels: { id: string; owned_by: string }[] = [];
	let selectedModel = '';
	let loading = false;
	let error = '';
	let messageInput = '';
	let messages: ChatMessage[] = [];
	let streaming = false;
	let currentResponse = '';
	let abortController: AbortController | null = null;

	// Load available models on mount
	onMount(async () => {
		try {
			const response = await api.listAvailableModels();
			availableModels = response.data;
			if (availableModels.length > 0) {
				selectedModel = availableModels[0].id;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load models';
		}
	});

	// Send message
	async function sendMessage() {
		if (!messageInput.trim() || !selectedModel || streaming) {
			return;
		}

		// Add user message to history
		const userMessage: ChatMessage = {
			role: 'user',
			content: messageInput.trim()
		};
		messages = [...messages, userMessage];
		messageInput = '';

		// Start streaming response
		streaming = true;
		currentResponse = '';
		error = '';
		abortController = new AbortController();

		try {
			// Stream the completion
			const stream = streamChatCompletion(
				{
					model: selectedModel,
					messages: messages,
					stream: true
				},
				{
					signal: abortController.signal,
					onToken: (token) => {
						currentResponse += token;
					},
					onDone: () => {
						// Add assistant message to history
						if (currentResponse) {
							messages = [
								...messages,
								{
									role: 'assistant',
									content: currentResponse
								}
							];
						}
						currentResponse = '';
						streaming = false;
						abortController = null;
					},
					onError: (err) => {
						error = err.message;
						streaming = false;
						abortController = null;
					}
				}
			);

			// Consume the stream
			for await (const _ of stream) {
				// Tokens are handled by onToken callback
			}
		} catch (err) {
			if (err instanceof Error && err.name !== 'AbortError') {
				error = err.message;
			}
			streaming = false;
			abortController = null;
		}
	}

	// Stop streaming
	function stopStreaming() {
		if (abortController) {
			abortController.abort();
		}
		if (currentResponse) {
			messages = [
				...messages,
				{
					role: 'assistant',
					content: currentResponse
				}
			];
		}
		currentResponse = '';
		streaming = false;
		abortController = null;
	}

	// Clear chat history
	function clearChat() {
		messages = [];
		currentResponse = '';
		error = '';
		streaming = false;
		if (abortController) {
			abortController.abort();
			abortController = null;
		}
	}

	// Handle Enter key in textarea
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}
</script>

<div class="chat-page">
	<div class="chat-header">
		<h1>Chat Interface</h1>
		<div class="controls">
			<div class="model-selector">
				<label for="model">Model:</label>
				<select id="model" bind:value={selectedModel} disabled={streaming || availableModels.length === 0}>
					{#if availableModels.length === 0}
						<option value="">Loading models...</option>
					{:else}
						{#each availableModels as model}
							<option value={model.id}>{model.id}</option>
						{/each}
					{/if}
				</select>
			</div>
			<button class="clear-btn" on:click={clearChat} disabled={streaming}>
				Clear Chat
			</button>
		</div>
	</div>

	{#if error}
		<div class="error-banner">
			<strong>Error:</strong> {error}
		</div>
	{/if}

	<div class="chat-container">
		<div class="messages-container">
			{#if messages.length === 0 && !currentResponse}
				<div class="empty-state">
					<p>No messages yet. Start a conversation!</p>
				</div>
			{:else}
				{#each messages as message}
					<div class="message message-{message.role}">
						<div class="message-header">
							<strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
						</div>
						<div class="message-content">
							{message.content}
						</div>
					</div>
				{/each}

				{#if currentResponse}
					<div class="message message-assistant">
						<div class="message-header">
							<strong>Assistant</strong>
							<span class="streaming-indicator">Streaming...</span>
						</div>
						<div class="message-content">
							{currentResponse}
							<span class="cursor">▊</span>
						</div>
					</div>
				{/if}
			{/if}
		</div>

		<div class="input-container">
			<textarea
				bind:value={messageInput}
				on:keydown={handleKeydown}
				placeholder="Type your message... (Shift+Enter for new line)"
				disabled={streaming || !selectedModel}
				rows="3"
			></textarea>
			<div class="input-actions">
				{#if streaming}
					<button class="stop-btn" on:click={stopStreaming}>
						Stop
					</button>
				{:else}
					<button
						class="send-btn"
						on:click={sendMessage}
						disabled={!messageInput.trim() || !selectedModel}
					>
						Send
					</button>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.chat-page {
		padding: 2rem;
		max-width: 1200px;
		margin: 0 auto;
		height: calc(100vh - 4rem);
		display: flex;
		flex-direction: column;
	}

	.chat-header {
		margin-bottom: 1.5rem;
	}

	h1 {
		font-size: 2rem;
		margin-bottom: 1rem;
		color: #1a1a1a;
	}

	.controls {
		display: flex;
		gap: 1rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.model-selector {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.model-selector label {
		font-weight: 500;
		color: #495057;
	}

	.model-selector select {
		padding: 0.5rem 1rem;
		border: 1px solid #ced4da;
		border-radius: 4px;
		font-size: 0.875rem;
		background: white;
		min-width: 200px;
	}

	.model-selector select:disabled {
		background: #e9ecef;
		cursor: not-allowed;
	}

	.clear-btn {
		padding: 0.5rem 1rem;
		background: #6c757d;
		color: white;
		border: none;
		border-radius: 4px;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background 0.2s;
	}

	.clear-btn:hover:not(:disabled) {
		background: #5a6268;
	}

	.clear-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.error-banner {
		padding: 1rem;
		background: #f8d7da;
		border: 1px solid #f5c6cb;
		border-radius: 4px;
		color: #721c24;
		margin-bottom: 1rem;
	}

	.chat-container {
		flex: 1;
		display: flex;
		flex-direction: column;
		background: white;
		border: 1px solid #dee2e6;
		border-radius: 8px;
		overflow: hidden;
	}

	.messages-container {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.empty-state {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #6c757d;
		font-style: italic;
	}

	.message {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-width: 80%;
	}

	.message-user {
		align-self: flex-end;
	}

	.message-assistant {
		align-self: flex-start;
	}

	.message-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: #6c757d;
	}

	.streaming-indicator {
		font-size: 0.75rem;
		color: #007bff;
		font-style: italic;
	}

	.message-content {
		padding: 1rem;
		border-radius: 8px;
		white-space: pre-wrap;
		word-wrap: break-word;
	}

	.message-user .message-content {
		background: #007bff;
		color: white;
	}

	.message-assistant .message-content {
		background: #f8f9fa;
		color: #212529;
		border: 1px solid #dee2e6;
	}

	.cursor {
		animation: blink 1s infinite;
		color: #007bff;
	}

	@keyframes blink {
		0%, 50% { opacity: 1; }
		51%, 100% { opacity: 0; }
	}

	.input-container {
		border-top: 1px solid #dee2e6;
		padding: 1rem;
		background: #f8f9fa;
	}

	textarea {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #ced4da;
		border-radius: 4px;
		font-family: inherit;
		font-size: 0.875rem;
		resize: vertical;
		min-height: 80px;
	}

	textarea:focus {
		outline: none;
		border-color: #007bff;
		box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
	}

	textarea:disabled {
		background: #e9ecef;
		cursor: not-allowed;
	}

	.input-actions {
		margin-top: 0.75rem;
		display: flex;
		justify-content: flex-end;
	}

	.send-btn, .stop-btn {
		padding: 0.5rem 2rem;
		border: none;
		border-radius: 4px;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}

	.send-btn {
		background: #007bff;
		color: white;
	}

	.send-btn:hover:not(:disabled) {
		background: #0056b3;
	}

	.send-btn:disabled {
		background: #6c757d;
		opacity: 0.5;
		cursor: not-allowed;
	}

	.stop-btn {
		background: #dc3545;
		color: white;
	}

	.stop-btn:hover {
		background: #c82333;
	}
</style>
