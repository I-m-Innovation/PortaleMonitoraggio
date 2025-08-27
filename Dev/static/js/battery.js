navigator.getBattery()
	.then(function (battery) {
		window.battery = battery;
		window.indicator = document.querySelector('#indicator');
		handleBattery();
	});

function handleBattery() {
	if (battery) {
		battery.addEventListener('chargingchange', updateBatteryStatus);
		battery.addEventListener('levelchange', updateBatteryStatus);
		updateBatteryStatus();
	}
}

function updateBatteryStatus() {
	if (battery.level * 100 === 100) indicator.style.width = '70%';
	else indicator.style.width = battery.level * 100 + '%';

	indicator.className = battery.charging ? 'charging' : 'notCharging';
}