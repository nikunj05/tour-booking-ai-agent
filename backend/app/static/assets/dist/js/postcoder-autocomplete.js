class PostcoderAutocomplete {
    constructor(config) {
        this.apiKey = document.querySelector(config.apikey).value;
        this.searchBox = document.querySelector(config.searchterm);
        this.suggestionList = document.querySelector(config.suggestions);
        this.countryCode = config.countrycode || "UK";

        this.fields = {
            addressline1: document.querySelector(config.addressline1),
            addressline2: document.querySelector(config.addressline2),
            posttown: document.querySelector(config.posttown),
            postcode: document.querySelector(config.postcode)
        };

        this.init();
    }

    init() {
        this.searchBox.addEventListener("input", () => this.fetchSuggestions());
    }

    async fetchSuggestions() {
        const query = this.searchBox.value.trim();
        if (query.length < 3) return this.clearSuggestions();

        try {
            const url = `https://ws.postcoder.com/pcw/${this.apiKey}/autocomplete/find?query=${query}&country=${this.countryCode}`;
            const response = await fetch(url);

            if (!response.ok) throw new Error("Network error");

            const results = await response.json();
            this.renderSuggestions(results);
        } catch (err) {
            console.error("Suggestion API Error:", err);
            this.clearSuggestions();
        }
    }

    renderSuggestions(results) {
        this.clearSuggestions();
        results.forEach(result => {
            const li = document.createElement("li");
            li.textContent = result.s;
            li.style.padding = "8px";
            li.style.cursor = "pointer";
            li.addEventListener("click", () => this.selectSuggestion(result));
            this.suggestionList.appendChild(li);
        });
    }

    clearSuggestions() {
        this.suggestionList.innerHTML = "";
    }

    async selectSuggestion(suggestion) {
        try {
            const url = `https://ws.postcoder.com/pcw/${this.apiKey}/address/uk/${suggestion.i}`;
            const response = await fetch(url);
            const data = await response.json();

            const address = data[0];
            this.fields.addressline1.value = address.addressline1 || "";
            this.fields.addressline2.value = address.addressline2 || "";
            this.fields.posttown.value = address.posttown || "";
            this.fields.postcode.value = address.postcode || "";

            this.clearSuggestions();
        } catch (err) {
            console.error("Error fetching address details", err);
        }
    }
}
