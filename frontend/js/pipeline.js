/* ============================================================
   pipeline.js — Pipeline Page Animations
   ============================================================ */

function setupPipelineAnimations() {
  // Stagger the reveal animations for timeline steps
  const steps = document.querySelectorAll('.timeline-step');
  steps.forEach((step, i) => {
    step.style.transitionDelay = `${i * 0.1}s`;
  });

  // Animate architecture diagram blocks
  const archBlocks = document.querySelectorAll('.arch-block');
  archBlocks.forEach((block, i) => {
    block.style.opacity = '0';
    block.style.transform = 'translateY(20px)';
    block.style.transition = `all 0.5s cubic-bezier(0.16, 1, 0.3, 1) ${0.2 + i * 0.1}s`;

    // Trigger after a small delay
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        block.style.opacity = '1';
        block.style.transform = 'translateY(0)';
      });
    });
  });

  // Animate arrows
  const arrows = document.querySelectorAll('.arch-arrow');
  arrows.forEach((arrow, i) => {
    arrow.style.opacity = '0';
    arrow.style.transition = `opacity 0.4s ease ${0.3 + i * 0.1}s`;

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        arrow.style.opacity = '0.6';
      });
    });
  });
}
