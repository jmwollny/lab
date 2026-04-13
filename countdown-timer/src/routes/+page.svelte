<script>
	import Countdown from '$lib/components/Countdown.svelte';
	import { onMount } from 'svelte';
	// let countdownTimes = [
	// 	{
	// 		name: 'Snowdon trip',
	// 		date: '2025-05-22:18:00'
	// 	},
	// 	{
	// 		name: "Mia's birthday",
	// 		date: '2026-01-18:00:00'
	// 	},
	// 	{
	// 		name: "Jake's birthday",
	// 		date: '2025-03-16:18:00'
	// 	},
	// 	{
	// 		name: "Rowena's birthday",
	// 		date: '2025-05-22:18:00',
	// 		colour: 'fuchsia'
	// 	}
	// ];
	/** @type {{id: number, name?: string; date: string; colour?: string; }[]}  */
	let countdownTimes = [];
	onMount(async () => {
		const timers = await fetch("http://localhost:3000/api/timers");
		const jsonResponse = await timers.json();
		countdownTimes = jsonResponse.map((/** @type {{ name: string; date: string; colour?: string; }} */ timer) => {
			return {
				name: timer.name,
				date: timer.date,
				colour: timer.colour
			};
		});
	});
</script>

{#each countdownTimes as countdown}
	<Countdown name={countdown.name} date={countdown.date} colour={countdown.colour} />
{/each}

<!-- <Countdown name="Snowdon trip" date="2025-05-22:18:00" />
<Countdown name="Mia's birthday" date="2026-01-18:00:00" />
<Countdown name="Jake's birthday" date="2026-03-16:00:00" />
<Countdown name="Jonathan's birthday" date="2025-06-25:00:00" />
<Countdown name="Rowena's birthday" date="2025-09-13:00:00" colour="fuchsia" /> -->
