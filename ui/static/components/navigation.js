/**
 * Navigation Component
 * Handles section navigation and data loading
 */

import {
    getElement,
    querySelectorAll
} from '../utils/helpers.js';

class NavigationManager {
    constructor() {
        this.sectionLoaders = new Map();
        this.currentSection = null;
    }

    /**
     * Register a section loader function
     * @param {string} sectionId - Section ID
     * @param {Function} loader - Loader function
     */
    registerLoader(sectionId, loader) {
        this.sectionLoaders.set(sectionId, loader);
    }

    /**
     * Load section-specific data
     * @param {string} sectionId - Section ID to load
     */
    async loadSectionData(sectionId) {
        try {
            const loader = this.sectionLoaders.get(sectionId);
            if (loader && typeof loader === 'function') {
                await loader();
            }
        } catch (error) {
            console.error(`Failed to load section ${sectionId}:`, error);
        }
    }

    /**
     * Show a section and hide others
     * @param {string} sectionId - Section ID to show
     * @param {HTMLElement} eventElement - Element that triggered the navigation
     */
    showSection(sectionId, eventElement) {
        try {
            // Hide all sections - remove both class and inline styles
            const allSections = querySelectorAll('.section');
            allSections.forEach(s => {
                s.classList.remove('active');
                // Remove inline display style that might override CSS
                s.style.display = '';
            });

            // Show selected section
            const targetSection = getElement(sectionId);
            if (!targetSection) {
                console.error('Section not found:', sectionId);
                return;
            }
            targetSection.classList.add('active');
            // Ensure inline style doesn't override (CSS will handle display via .active class)
            targetSection.style.display = '';
            this.currentSection = sectionId;

            // Update active nav item
            const navLinks = querySelectorAll('.nav-menu a');
            navLinks.forEach(a => a.classList.remove('active'));

            if (eventElement) {
                eventElement.classList.add('active');
            } else {
                navLinks.forEach(a => {
                    const onclick = a.getAttribute('onclick');
                    if (onclick && onclick.includes(sectionId)) {
                        a.classList.add('active');
                    }
                });
            }

            // Load section-specific data
            this.loadSectionData(sectionId);
        } catch (error) {
            console.error('Error in showSection:', error);
        }
    }

    /**
     * Initialize navigation
     */
    init() {
        // Enhance inline showSection if it exists
        if (typeof window.showSection === 'function') {
            const originalShowSection = window.showSection;
            window.showSection = (sectionId, eventElement) => {
                originalShowSection(sectionId, eventElement);
                this.showSection(sectionId, eventElement);
            };
        } else {
            window.showSection = (sectionId, eventElement) => {
                this.showSection(sectionId, eventElement);
            };
        }

        // Set up navigation button event listeners
        document.addEventListener('DOMContentLoaded', () => {
            querySelectorAll('.nav-menu a').forEach(link => {
                const onclick = link.getAttribute('onclick');
                if (onclick && onclick.includes('showSection')) {
                    const match = onclick.match(/showSection\(['"]([^'"]+)['"]/);
                    if (match) {
                        const sectionId = match[1];
                        link.removeAttribute('onclick');
                        link.addEventListener('click', (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            this.showSection(sectionId, link);
                            return false;
                        });
                    }
                }
            });
        });
    }
}

export const navigationManager = new NavigationManager();