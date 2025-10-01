function toLocaleEUR(data,d) {
        data = parseFloat(data)
        return data.toLocaleString('it-IT', { style: 'currency', currency: "EUR", maximumFractionDigits: d});
}

function toLocaleKWh(data,d) {
        data = parseFloat(data)
        return data.toLocaleString('it-IT', { style: 'decimal', maximumFractionDigits: d}) + ' kWh';
}

function toLocale(data,d) {
        data = parseFloat(data)
        return data.toLocaleString('it-IT', { style: 'decimal', maximumFractionDigits: d});
}

function toLocaleDate(data) {
        return new Date(data).toLocaleDateString('it-IT',{month: 'long',year:'numeric'})
}

function getRandomArbitrary(min, max) {
        return Math.random() * (max - min) + min;
}