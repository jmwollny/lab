<script>
	import { onMount } from 'svelte';
	/**
	 * @type {{ total: any; days: any; hours: any; minutes: any; seconds: any; }}
	 */
	let timeLeft = $state({
		total: 0,
		days: 0,
		hours: 0,
		minutes: 0,
		seconds: 0
	});

	/**
	 * @typedef {Object} Props
	 * @property {string} [name]
	 * @property {string} [date]
	 * @property {string} [colour]
	 */

	/** @type {Props} */
	let { date = '', colour = 'white', name = '' } = $props();

	/**
	 * @type {number | undefined}
	 */
	let timerInterval;

	let expired = $state(false);
	let loaded = $state(false);
	let closed = $state(false);

	const dueDate = new Date(date);
	const closeCountdown = () => {
		closed = true;
	};
	const formattedDate = (/** @type {Date} */ date, short = false) => {
		let formatter;
		if (short) {
			formatter = new Intl.DateTimeFormat('en-GB');
		} else {
			formatter = new Intl.DateTimeFormat('en-GB', {
				dateStyle: 'full',
				timeStyle: 'short',
				timeZone: 'Europe/London'
			});
		}

		return formatter.format(date);
	};
	const calculateTimeLeft = () => {
		const difference = dueDate.getTime() - new Date().getTime();
		if (difference > 0) {
			return {
				total: difference,
				days: Math.floor(difference / (1000 * 60 * 60 * 24)),
				hours: Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
				minutes: Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60)),
				seconds: Math.floor((difference % (1000 * 60)) / 1000)
			};
		} else {
			expired = true;
			return {
				total: 0,
				days: 0,
				hours: 0,
				minutes: 0,
				seconds: 0
			};
		}
	};
	const getButtonLabel = () => {
		if (expired) {
			return 'Close';
		} else {
			return 'Delete';
		}
	};
	const getBackgroundColour = () => {
		if (expired) {
			return 'red';
		} else {
			return colour;
		}
	};
	onMount(() => {
		timerInterval = setInterval(() => {
			timeLeft = calculateTimeLeft();
			loaded = true;
			if (expired) {
				clearInterval(timerInterval);
			}
		}, 1000);
		// Cleanup on unmount
		return () => clearInterval(timerInterval);
	});
</script>

{#if loaded && !closed}
	<div class="countdown" style="--tile-colour: {getBackgroundColour()}">
		<div class="title">
			{name} - {formattedDate(dueDate, false)}
			<button onclick={closeCountdown}>{getButtonLabel()}</button>
		</div>

		{#if expired}
			<div class="expired">The timer has expired!</div>
		{/if}
		{#if !expired}
			<div>
				<div class="header">
					<div>Days</div>
					<div>Hours</div>
					<div>Minutes</div>
					<div>Seconds</div>
				</div>
				<div class="details">
					<div>{timeLeft.days}</div>
					<div>{timeLeft.hours}</div>
					<div>{timeLeft.minutes}</div>
					<div>{timeLeft.seconds}</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.countdown {
		font-family: Verdana, Geneva, Tahoma, sans-serif;
		padding: 0.5rem;
		margin-top: 0.5rem;
		background-color: var(--tile-colour);
		border-radius: 5px;
		height: 7rem;
	}
	.title {
		display: flex;
		justify-content: space-between;
		font-weight: bold;
	}
	.header,
	.details {
		display: flex;
		font-size: 1.5rem;
		justify-content: space-between;
	}
	button {
		width: 50px;
		height: 25px;
	}
</style>
