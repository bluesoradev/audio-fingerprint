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
     * Update content-area height for manipulate section based on test results
     * @param {HTMLElement} contentArea - Content area element
     */
    updateManipulateContentHeight(contentArea) {
        const testResultsContent = getElement('testResultsContent');
        if (!testResultsContent) {
            // Default to 1200px if test results container not found
            contentArea.classList.add('content-area-manipulate');
            return;
        }

        // Check if test results have actual test data (not just system logs)
        const hasTestResults = this.hasActualTestResults(testResultsContent);
        
        if (hasTestResults) {
            contentArea.classList.remove('content-area-manipulate');
            contentArea.classList.add('content-area-manipulate-with-results');
        } else {
            contentArea.classList.remove('content-area-manipulate-with-results');
            contentArea.classList.add('content-area-manipulate');
        }
    }

    /**
     * Check if test results content has actual test results (not just system logs)
     * @param {HTMLElement} testResultsContent - Test results content element
     * @returns {boolean} - True if actual test results exist
     */
    hasActualTestResults(testResultsContent) {
        if (!testResultsContent) return false;
        
        const html = testResultsContent.innerHTML || '';
        const text = testResultsContent.textContent || '';
        
        // Check for indicators of actual test results (not just system logs)
        // Test results contain: similarity scores, rank, match status, error messages, etc.
        const hasSimilarity = html.includes('Similarity Score') || (html.includes('similarity') && /(\d+\.?\d*)%/.test(text));
        const hasRank = html.includes('Rank') || html.includes('rank');
        const hasMatchStatus = html.includes('Strong match') || html.includes('Good match') || 
                              html.includes('Moderate match') || html.includes('could not match') ||
                              html.includes('robust to this transformation');
        const hasErrorResult = html.includes('Error testing fingerprint') || html.includes('Error:');
        const hasPercent = /(\d+\.?\d*)%/.test(text) && (hasSimilarity || hasMatchStatus);
        
        // If it has similarity score, match status, or error from test, it's actual test results
        // Exclude system initialization messages
        const isSystemLog = text.includes('System initialized') || text.includes('Ready for audio input');
        const hasTestContent = (hasSimilarity && (hasRank || hasMatchStatus || hasPercent)) || hasErrorResult;
        
        return hasTestContent && !isSystemLog;
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
            // Hide all sections - explicitly set display: none to override any inline styles
            const allSections = querySelectorAll('.section');
            allSections.forEach(s => {
                s.classList.remove('active');
                // Force hide with inline style to override any conflicting styles
                s.style.display = 'none';
            });

            // Show selected section
            const targetSection = getElement(sectionId);
            if (!targetSection) {
                console.error('Section not found:', sectionId);
                return;
            }
            targetSection.classList.add('active');
            // Remove inline style so CSS .active class can control visibility
            targetSection.style.display = '';
            this.currentSection = sectionId;

            // Toggle content-area height based on section
            const contentArea = querySelectorAll('.content-area')[0];
            if (contentArea) {
                // Dashboard doesn't need full height
                if (sectionId === 'dashboard') {
                    contentArea.classList.remove('content-area-full', 'content-area-manipulate', 'content-area-manipulate-with-results');
                    contentArea.classList.add('dashboard-content-area');
                } else if (sectionId === 'manipulate') {
                    // Manipulate section height depends on test results
                    contentArea.classList.remove('dashboard-content-area', 'content-area-full', 'content-area-manipulate-with-results');
                    this.updateManipulateContentHeight(contentArea);
                } else {
                    // Other sections (deliverables, etc.) need full height
                    contentArea.classList.remove('dashboard-content-area', 'content-area-manipulate', 'content-area-manipulate-with-results');
                    contentArea.classList.add('content-area-full');
                }
            }

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

        // Set up navigation button event listeners and initialize sections
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize: hide all sections except the one marked as active
            const allSections = querySelectorAll('.section');
            let activeSectionId = null;
            allSections.forEach(s => {
                if (!s.classList.contains('active')) {
                    s.style.display = 'none';
                } else {
                    s.style.display = '';
                    activeSectionId = s.id;
                }
            });

            // Initialize content-area height based on active section
            const contentArea = querySelectorAll('.content-area')[0];
            if (contentArea && activeSectionId) {
                if (activeSectionId === 'dashboard') {
                    contentArea.classList.remove('content-area-full', 'content-area-manipulate', 'content-area-manipulate-with-results');
                    contentArea.classList.add('dashboard-content-area');
                } else if (activeSectionId === 'manipulate') {
                    contentArea.classList.remove('dashboard-content-area', 'content-area-full', 'content-area-manipulate-with-results');
                    this.updateManipulateContentHeight(contentArea);
                } else {
                    contentArea.classList.remove('dashboard-content-area', 'content-area-manipulate', 'content-area-manipulate-with-results');
                    contentArea.classList.add('content-area-full');
                }
            }

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