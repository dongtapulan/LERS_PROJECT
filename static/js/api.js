// Centralized API handler for LERS frontend operations
const LERS_API = {
    async updateReservation(resId, action) {
        try {
            const response = await fetch(`/update_reservation/${resId}/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            return await response.json();
        } catch (error) {
            console.error("API error during reservation processing:", error);
            return { success: false, message: "Network connection failure." };
        }
    }
};