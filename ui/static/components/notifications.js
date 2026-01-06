/**
 * Notification Component
 * Handles user notifications, alerts, and error messages
 */

class NotificationManager {
    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        alert('Error: ' + message);
        this.addSystemLog('Error: ' + message, 'error');
    }

    /**
     * Show completion alert
     * @param {string} message - Alert message
     * @param {string} type - Alert type (success, error, warning, info)
     */
    showCompletionAlert(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : type === 'warning' ? '#ff9800' : '#2196F3'};
            color: white;
            padding: 20px 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            font-size: 16px;
            font-weight: 500;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        `;

        alertDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">${this.getIcon(type)}</span>
                <span>${message}</span>
            </div>
        `;

        // Add animation style if not already added
        if (!document.getElementById('alertAnimationStyle')) {
            const style = document.createElement('style');
            style.id = 'alertAnimationStyle';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(alertDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            alertDiv.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 300);
        }, 5000);

        // Show browser alert for important notifications
        if (type === 'success') {
            alert(message);
        }
    }

    /**
     * Show notification (simpler than completion alert)
     * @param {string} message - Notification message
     * @param {string} type - Notification type
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#f87171' : '#427eea'};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Add system log (kept for compatibility, currently no-op)
     * @param {string} message - Log message
     * @param {string} type - Log type
     */
    addSystemLog(message, type = 'info') {
        // Logs section removed - function kept for compatibility
        return;
    }

    /**
     * Get icon for notification type
     * @param {string} type - Notification type
     * @returns {string} Icon character
     */
    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || 'ℹ';
    }
}

export const notificationManager = new NotificationManager();

// Export convenience functions
export const showError = (message) => notificationManager.showError(message);
export const showCompletionAlert = (message, type) => notificationManager.showCompletionAlert(message, type);
export const showNotification = (message, type) => notificationManager.showNotification(message, type);
export const addSystemLog = (message, type) => notificationManager.addSystemLog(message, type);