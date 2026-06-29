// src/services/api.js
const BASE_URL = "http://127.0.0.1:8000/api";

export const sessionService = {
  async getSummary() {
    try {
      const response = await fetch(`${BASE_URL}/session/summary/`);
      if (!response.ok) throw new Error("Network response was not ok");
      return await response.json();
    } catch (error) {
      console.error("API Error:", error);
      throw error;
    }
  }
};