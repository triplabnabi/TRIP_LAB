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
          // Performance optimizations
          postprocessing: {
            occlusion: { name: 'off' },
            shadow: { name: 'off' },
          },
        });

        // Further performance optimization
        this.viewer.plugin.canvas3d.setProps({
          renderer: {
            ...this.viewer.plugin.canvas3d.props.renderer,
            dpr: window.devicePixelRatio < 2 ? window.devicePixelRatio : 1,
          }
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

        const tooltip = document.createElement('span');
        tooltip.className = 'tooltip';
        tooltip.textContent = button.dataset.tooltip;
        button.appendChild(tooltip);
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

        // Simplified cartoon representation for performance
        await plugin.builders.structure.representation.addRepresentation(structureData, {
            type: 'cartoon',
            color: 'secondary-structure',
            size: 'uniform',
            sizeParams: { value: 0.8 }
        });

        plugin.managers.camera.reset();

        console.log(`Loaded ${structure.pdbId} (${structure.description})`);

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
