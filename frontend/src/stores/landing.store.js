import { defineStore } from "pinia";
import { landingApi } from "../api/landing.api";

export const useLandingStore = defineStore("landing", {
  state: () => ({
    hero: null,
    about: null,
    features: [],
    team: [],
    locations: [],
    settings: null,
    loaded: false,
    error: null,
  }),
  actions: {
    async loadAll() {
      this.error = null;
      try {
        const [hero, about, features, team, locations, settings] = await Promise.all([
          landingApi.getHero().catch(() => null),
          landingApi.getAbout().catch(() => null),
          landingApi.getFeatures().catch(() => []),
          landingApi.getTeam().catch(() => []),
          landingApi.getLocations().catch(() => []),
          landingApi.getSiteSettings().catch(() => null),
        ]);
        this.hero = hero;
        this.about = about;
        this.features = features;
        this.team = team;
        this.locations = locations;
        this.settings = settings;
      } catch (e) {
        this.error = e;
      } finally {
        this.loaded = true;
      }
    },
  },
});
