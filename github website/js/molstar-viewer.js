/**
 * TR(i)P Lab - Molstar Molecular Viewer
 * Version: 3.0 - Corrected and simplified
 */

(function() {
  "use strict";

  class TRPM8Viewer {
    constructor(containerId) {
      this.containerId = containerId;
      this.container = null;
      this.viewer = null;
      this.structures = {
        apoLike: { pdbId: '6O6A', description: 'Apo-like Structure', scientificName: 'Apo-like State' },
        closed: { pdbId: '6NR3', description: 'Voltage-Sensitive Closed', scientificName: 'Closed Conformation' },
        intermediate: { pdbId: '6NR2', description: 'Menthol-Trapped', scientificName: 'WS-12/Menthol Analog Complex' },
        open: { pdbId: '5ICE', description: 'Fully Activated Open', scientificName: 'Menthol-Bound Active' }
      };
      this.currentState = 'closed';
    }

    async initialize() {
      this.container = document.getElementById(this.containerId);
      if (!this.container) {
        console.error('Molstar container not found');
        return false;
      }

      if (typeof window.molstar === 'undefined') {
        this.showError('Molstar library not loaded. Please check your internet connection.');
        return false;
      }

      try {
        this.viewer = await window.molstar.Viewer.create(this.container, {
          layoutIsExpanded: false,
          layoutShowControls: false,
          layoutShowRemoteState: false,
          layoutShowSequence: false,
          layoutShowLog: false,
          layoutShowLeftPanel: false,
          viewportShowExpand: true,
          viewportShowSelectionMode: false,
        });

        this.setupUIInteractions();
        await this.loadStructure(this.currentState);
        const initialButton = document.querySelector(`.trpm8-state-btn[data-state="${this.currentState}"]`);
        if (initialButton) {
            this.updateActiveStateVisual(initialButton);
        }
        this.setupInteractivity();
        return true;

      } catch (error) {
        console.error('Failed to initialize Molstar:', error);
        this.showError('Failed to load 3D viewer.');
        return false;
      }
    }

    setupUIInteractions() {
      const stateButtons = document.querySelectorAll('.trpm8-state-btn');
      stateButtons.forEach(button => {
        button.addEventListener('click', () => {
          const state = button.dataset.state;
          if (state && this.structures[state]) {
            this.loadStructure(state);
            this.updateActiveStateVisual(button);
          }
        });
      });
    }

    async loadStructure(state) {
      if (!this.viewer || !this.structures[state]) return;

      this.currentState = state;
      const structure = this.structures[state];
      const loadingIndicator = document.getElementById('loading-indicator');
      const plugin = this.viewer.plugin;

      if (loadingIndicator) loadingIndicator.style.display = 'block';

      try {
        await plugin.clear();

        const data = await plugin.builders.data.download({ url: `https://files.rcsb.org/download/${structure.pdbId}.pdb` });
        const trajectory = await plugin.builders.structure.parseTrajectory(data, 'pdb');
        
        const model = await plugin.builders.structure.createModel(trajectory);
        const structureData = await plugin.builders.structure.createStructure(model);

        // Enhanced surface representation with secondary structure coloring
        // This makes the TRP channel scientifically informative and visually appealing
        await plugin.builders.structure.representation.addRepresentation(structureData, {
            type: 'gaussian-surface',
            color: 'secondary-structure',
            colorParams: {
                helix: { r: 0.1, g: 0.4, b: 0.9 },    // Helices: Blue
                sheet: { r: 0.9, g: 0.1, b: 0.1 },    // Sheets: Red
                loop: { r: 0.5, g: 0.5, b: 0.5 }      // Loops: Gray
            },
            alpha: 0.3 // Perfect balance: informative yet not overpowering
        });

        // Add the cartoon representation inside
        await plugin.builders.structure.representation.addRepresentation(structureData, {
            type: 'cartoon',
            color: 'sequence-id'
        });

        plugin.managers.camera.reset();

        console.log(`Loaded ${structure.pdbId} (${structure.description})`);

        // 🆕 TRIGGER SPIN ANIMATION AFTER STRUCTURE IS FULLY READY
        console.log('⏳ Preparing spin animation after structure loads...');
        setTimeout(() => {
          console.log('🎬 Starting Cinematic Spin Animation!');
          this.animateSpinReveal(plugin, 12000); // 12-second slower spin
        }, 2500); // Wait 2.5 seconds for full structure rendering + centering

      } catch (error) {
        console.error(`Failed to load structure ${structure.pdbId}:`, error);
        this.showError(`Failed to load PDB: ${structure.pdbId}`);
      } finally {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
      }
    }

    setupInteractivity() {
        const plugin = this.viewer.plugin;
        plugin.behaviors.interaction.hover.subscribe(event => {
            if (event.loci && event.loci.kind === 'structure-element-loci') {
                plugin.managers.interactivity.lociHighlights.highlightOnly({ loci: event.loci });
            }
        });
        plugin.behaviors.interaction.click.subscribe(event => {
            if (event.loci && event.loci.kind === 'structure-element-loci') {
                plugin.managers.camera.focusLoci(event.loci);
            }
        });
    }

    updateActiveStateVisual(activeButton) {
      const stateButtons = document.querySelectorAll('.trpm8-state-btn');
      stateButtons.forEach(button => {
        button.classList.remove('active');
      });
      activeButton.classList.add('active');
    }

    /**
     * Create cinematic one-time spin animation to reveal the loaded structure
     * @param {Object} plugin - Molstar plugin instance
     * @param {number} duration - Animation duration in milliseconds (default: 12 seconds)
     */
    async animateSpinReveal(plugin, duration = 12000) {
      try {
        console.log('🎯 Starting ULTRA-smooth cinematic spin animation...');

        const camera = plugin.canvas3d.camera;
        const rotationSteps = 72; // 72 steps for SILKY-smooth 360° (5° per step)
        const stepDuration = duration / rotationSteps;

        // Get initial camera position
        await plugin.managers.camera.reset();
        let currentSnapshot = camera.getSnapshot();

        console.log(`🎬 CINEMATIC ANIM: ${duration}ms total, ${rotationSteps} steps, ${Math.round(stepDuration)}ms per step`);

        // Store the original position and target
        const originalPosition = [...currentSnapshot.position];
        const originalTarget = [...currentSnapshot.target];
        const originalUp = [...currentSnapshot.up];

        // 🔍 FINE-TUNE CAMERA FOR TRPM8 PERFECT VIEWING
        // TRPM8 channels (~1100 AA) need optimal zoom for scientific viewing
        const scientificZoomFactor = 1.5; // 1.5x zoom for perfect channel proximity

        // Move camera to ideal scientific viewing position
        const scientificPosition = [
          originalPosition[0] * scientificZoomFactor, // Optimal X-distance
          originalPosition[1],                         // Standard height
          originalPosition[2] * scientificZoomFactor  // Optimal Z-distance
        ];

        // Define molecule center for smooth orbital motion
        const moleculeCenter = [
          originalTarget[0],
          originalTarget[1],
          originalTarget[2]
        ];

        console.log(`📸 SCIENTIFIC ZOOM: ${scientificZoomFactor}x - Perfect for TRPM8 channel viewing`);
        console.log(`🔬 Optimal balance: Shows complete architecture with ideal molecule size`);

        // Animation: Create circular camera motion around the molecule
        for (let step = 0; step <= rotationSteps; step++) {
          setTimeout(() => {
            const angle = (step / rotationSteps) * 2 * Math.PI; // Full 360° in radians

            // Calculate new camera position on circular orbit - ZOOMED OUT
            const radius = 220 * scientificZoomFactor; // Large orbit for complete TRPM8 view
            const heightOffset = 20; // Height variation for cinematic feel

            const newPosition = [
              moleculeCenter[0] + Math.sin(angle) * radius,
              moleculeCenter[1] + heightOffset,
              moleculeCenter[2] + Math.cos(angle) * radius
            ];

            // Create camera snapshot for this frame
            const stepSnapshot = {
              position: newPosition,
              target: originalTarget,
              up: originalUp
            };

            // Apply the camera movement
            plugin.managers.camera.setSnapshot(stepSnapshot, stepDuration / 2);

            // Log progress and completion
            if (step === rotationSteps) {
              console.log('✅ Spin animation complete!');

              // Optional: Return to a nice default view after spinning
              setTimeout(() => {
                plugin.managers.camera.reset();
                console.log('🎬 Animation finished - user has camera control');
              }, stepDuration);
            }

          }, step * stepDuration);
        }

      } catch (error) {
        console.warn('⚠️ Spin animation failed, continuing with default view:', error);
        // Fallback to basic view if animation fails
        try {
          plugin.managers.camera.reset();
        } catch (e) {
          console.error('❌ Failed to reset camera after animation error');
        }
      }
    }

    showError(message) {
      if (!this.container) return;
      this.container.innerHTML = `<div class="molstar-error" style="color: red; text-align: center; padding: 2rem;">${message}</div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('molstar-viewer')) {
      const viewer = new TRPM8Viewer('molstar-viewer');
      viewer.initialize();
    }
  });

})();
