/**
 * Online Examination System - Client-Side Interactive Engine
 */

document.addEventListener('DOMContentLoaded', () => {

    // -------------------------------------------------------------
    // 1. Auto-dismiss Flash Alerts
    // -------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert) => {
        const closeBtn = alert.querySelector('.alert-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 250);
            });
        }
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }
        }, 5000);
    });

    // -------------------------------------------------------------
    // 2. Demo Credentials Auto-Fill
    // -------------------------------------------------------------
    const demoFillButtons = document.querySelectorAll('[data-demo-user]');
    demoFillButtons.forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const usernameInput = document.getElementById('identifier');
            const passwordInput = document.getElementById('password');
            if (usernameInput && passwordInput) {
                const userType = btn.getAttribute('data-demo-user');
                if (userType === 'admin') {
                    usernameInput.value = 'dean@college.edu';
                    passwordInput.value = 'DeanSecret2026!';
                } else if (userType === 'student') {
                    usernameInput.value = 'student@college.edu';
                    passwordInput.value = 'StudentPass2026!';
                }
            }
        });
    });

    // -------------------------------------------------------------
    // 3. Online Examination Interactive Engine
    // -------------------------------------------------------------
    const examForm = document.getElementById('exam-submission-form');
    const timerDisplay = document.getElementById('exam-countdown-timer');

    if (examForm && timerDisplay) {
        const attemptId = examForm.getAttribute('data-attempt-id');
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : (examForm.querySelector('input[name="csrf_token"]')?.value || '');
        const autosaveIndicator = document.getElementById('autosave-indicator');
        const autosaveText = document.getElementById('autosave-text');

        // Helper to update autosave indicator badge
        function setAutosaveState(state) {
            if (!autosaveIndicator || !autosaveText) return;
            autosaveIndicator.classList.remove('saving', 'saved', 'error');
            if (state === 'saving') {
                autosaveIndicator.classList.add('saving');
                autosaveIndicator.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Saving...</span>';
            } else if (state === 'saved') {
                autosaveIndicator.classList.add('saved');
                autosaveIndicator.innerHTML = '<i class="fa-solid fa-cloud-check"></i> <span>Saved</span>';
            } else if (state === 'error') {
                autosaveIndicator.classList.add('error');
                autosaveIndicator.innerHTML = '<i class="fa-solid fa-cloud-exclamation"></i> <span>Save Failed</span>';
            }
        }

        // 3.1 Countdown Timer Logic (Server-synchronized)
        let totalSeconds = parseInt(timerDisplay.getAttribute('data-duration-seconds'), 10);
        if (isNaN(totalSeconds) || totalSeconds < 0) totalSeconds = 0;

        function updateTimer() {
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            timerDisplay.textContent = formatted;

            const timerContainer = timerDisplay.closest('.timer-box');
            if (timerContainer) {
                if (totalSeconds <= 60) { // Under 1 minute critical warning
                    timerContainer.classList.add('timer-critical');
                    timerContainer.classList.remove('timer-warning');
                } else if (totalSeconds <= 180) { // Under 3 minutes warning
                    timerContainer.classList.add('timer-warning');
                    timerContainer.classList.remove('timer-critical');
                } else {
                    timerContainer.classList.remove('timer-warning', 'timer-critical');
                }
            }

            if (totalSeconds <= 0) {
                clearInterval(timerInterval);
                timerDisplay.textContent = '00:00 (Submitting...)';
                // Automatically submit the exam when time expires
                isAutoSubmitting = true;
                const modal = document.getElementById('exam-submit-modal');
                if (modal) modal.classList.remove('is-open');
                examForm.submit();
            } else {
                totalSeconds--;
            }
        }

        updateTimer();
        const timerInterval = setInterval(updateTimer, 1000);
        let isAutoSubmitting = false;

        // 3.1b Live Exam Progress Bar Calculation
        function updateExamProgress() {
            const progressFill = document.getElementById('exam-progress-fill');
            const progressText = document.getElementById('exam-progress-text');
            if (!progressFill || !progressText) return;

            const totalQ = document.querySelectorAll('.question-block').length;
            if (totalQ === 0) return;
            const answeredQ = document.querySelectorAll('.mcq-options-group input[type="radio"]:checked').length;
            const percent = Math.round((answeredQ / totalQ) * 100);
            progressFill.style.width = `${percent}%`;
            progressText.textContent = `${percent}% Done`;
        }

        // Initialize progress bar on load
        updateExamProgress();

        // 3.1c Active Question Block Tracking
        function setActiveQuestion(block) {
            if (!block) return;
            document.querySelectorAll('.question-block.is-active-question').forEach(el => el.classList.remove('is-active-question'));
            block.classList.add('is-active-question');
        }

        const allQuestionBlocks = document.querySelectorAll('.question-block');
        if (allQuestionBlocks.length > 0) {
            setActiveQuestion(allQuestionBlocks[0]);
            allQuestionBlocks.forEach(block => {
                block.addEventListener('click', () => setActiveQuestion(block));
            });
        }

        // 3.2 Synchronize Question State & Palette Indicator
        function refreshQuestionStatus(questionId) {
            const qBlock = document.querySelector(`.question-block[data-question-id="${questionId}"]`);
            if (!qBlock) return;

            const selectedRadio = qBlock.querySelector('input[type="radio"]:checked');
            const reviewCheckbox = qBlock.querySelector('.mark-review-toggle');
            const reviewLabel = document.getElementById(`review-lbl-${questionId}`);
            const paletteBtn = document.getElementById(`palette-btn-${questionId}`);

            const isAnswered = Boolean(selectedRadio && selectedRadio.value);
            const isReview = Boolean(reviewCheckbox && reviewCheckbox.checked);

            // Update radio option label selection highlights
            qBlock.querySelectorAll('.mcq-option-label').forEach(lbl => {
                const radio = lbl.querySelector('input[type="radio"]');
                if (radio && radio.checked) {
                    lbl.classList.add('is-selected');
                } else {
                    lbl.classList.remove('is-selected');
                }
            });

            // Update review button active class
            if (reviewLabel) {
                if (isReview) {
                    reviewLabel.classList.add('is-active');
                } else {
                    reviewLabel.classList.remove('is-active');
                }
            }

            // Update palette button classes
            if (paletteBtn) {
                paletteBtn.classList.remove('palette-answered', 'palette-review', 'palette-answered-review');
                if (isAnswered && isReview) {
                    paletteBtn.classList.add('palette-answered-review');
                } else if (isAnswered) {
                    paletteBtn.classList.add('palette-answered');
                } else if (isReview) {
                    paletteBtn.classList.add('palette-review');
                }
            }
        }

        // 3.3 AJAX Autosave Endpoint Dispatcher
        function triggerAutosave(questionId) {
            const qBlock = document.querySelector(`.question-block[data-question-id="${questionId}"]`);
            if (!qBlock || !attemptId) return;

            const selectedRadio = qBlock.querySelector('input[type="radio"]:checked');
            const reviewCheckbox = qBlock.querySelector('.mark-review-toggle');

            const selectedValue = selectedRadio ? selectedRadio.value : '';
            const isReview = reviewCheckbox ? (reviewCheckbox.checked ? '1' : '0') : '0';

            setAutosaveState('saving');

            const formData = new FormData();
            formData.append('csrf_token', csrfToken);
            formData.append('question_id', questionId);
            formData.append('selected_option', selectedValue);
            formData.append('is_review', isReview);

            fetch(`/student/attempt/${attemptId}/save-answer`, {
                method: 'POST',
                headers: {
                    'X-CSRF-Token': csrfToken
                },
                body: formData
            })
            .then(res => {
                if (!res.ok) {
                    return res.json().then(data => { throw new Error(data.error || 'Autosave error'); });
                }
                return res.json();
            })
            .then(data => {
                if (data.expired) {
                    alert('Time limit has expired. Redirecting to results...');
                    window.location.reload();
                    return;
                }
                setAutosaveState('saved');
            })
            .catch(err => {
                console.error('Autosave sync failed:', err);
                setAutosaveState('error');
            });
        }

        // 3.4 Radio Button Change Listeners
        const mcqRadios = examForm.querySelectorAll('.mcq-options-group input[type="radio"]');
        mcqRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                const questionId = radio.getAttribute('data-question-id');
                const qBlock = document.querySelector(`.question-block[data-question-id="${questionId}"]`);
                refreshQuestionStatus(questionId);
                updateExamProgress();
                setActiveQuestion(qBlock);
                triggerAutosave(questionId);
            });
        });

        // 3.5 Mark for Review Listeners
        const reviewCheckboxes = examForm.querySelectorAll('.mark-review-toggle');
        reviewCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const questionId = cb.getAttribute('data-question-id');
                refreshQuestionStatus(questionId);
                triggerAutosave(questionId);
            });
        });

        // 3.6 Clear Choice Buttons
        const clearButtons = examForm.querySelectorAll('.btn-clear-choice');
        clearButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const questionId = btn.getAttribute('data-question-id');
                const qBlock = document.querySelector(`.question-block[data-question-id="${questionId}"]`);
                if (qBlock) {
                    const checkedRadio = qBlock.querySelector('input[type="radio"]:checked');
                    if (checkedRadio) {
                        checkedRadio.checked = false;
                        refreshQuestionStatus(questionId);
                        updateExamProgress();
                        triggerAutosave(questionId);
                    }
                }
            });
        });

        // 3.7 Question Palette Jump Scrolling
        const paletteButtons = document.querySelectorAll('.palette-btn[data-target-index]');
        paletteButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const index = btn.getAttribute('data-target-index');
                const targetBlock = document.querySelector(`.question-block[data-question-index="${index}"]`);
                if (targetBlock) {
                    targetBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    setActiveQuestion(targetBlock);
                    targetBlock.style.transition = 'box-shadow 0.3s ease';
                    targetBlock.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.4)';
                    setTimeout(() => {
                        targetBlock.style.boxShadow = '';
                    }, 1200);
                }
            });
        });

        // 3.8 In-Question Next / Previous Navigation
        const prevButtons = document.querySelectorAll('.nav-prev-btn');
        prevButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetIdx = btn.getAttribute('data-target-index');
                const targetBlock = document.querySelector(`.question-block[data-question-index="${targetIdx}"]`);
                if (targetBlock) {
                    targetBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    setActiveQuestion(targetBlock);
                }
            });
        });

        const nextButtons = document.querySelectorAll('.nav-next-btn');
        nextButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetIdx = btn.getAttribute('data-target-index');
                const targetBlock = document.querySelector(`.question-block[data-question-index="${targetIdx}"]`);
                if (targetBlock) {
                    targetBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    setActiveQuestion(targetBlock);
                }
            });
        });

        // 3.9 Interactive Submit Confirmation Modal
        const submitModal = document.getElementById('exam-submit-modal');
        const btnHeaderSubmit = document.getElementById('btn-header-submit');
        const btnBottomSubmit = document.getElementById('btn-bottom-submit');
        const btnModalCancel = document.getElementById('btn-modal-cancel');
        const btnModalConfirm = document.getElementById('btn-modal-confirm');

        function openSubmitModal() {
            if (!submitModal) {
                // Fallback to browser confirm
                if (confirm('Are you sure you want to finalize and submit your examination?')) {
                    examForm.submit();
                }
                return;
            }

            const totalQuestions = document.querySelectorAll('.question-block').length;
            const answeredCount = document.querySelectorAll('.mcq-options-group input[type="radio"]:checked').length;
            const reviewCount = document.querySelectorAll('.mark-review-toggle:checked').length;
            const unansweredCount = Math.max(0, totalQuestions - answeredCount);

            document.getElementById('modal-answered-count').textContent = answeredCount;
            document.getElementById('modal-review-count').textContent = reviewCount;
            document.getElementById('modal-unanswered-count').textContent = unansweredCount;

            const warningBox = document.getElementById('modal-warning-box');
            const warningText = document.getElementById('modal-warning-text');
            if (warningBox && warningText) {
                if (unansweredCount > 0 && reviewCount > 0) {
                    warningBox.style.display = 'block';
                    warningText.textContent = `You have ${unansweredCount} unanswered question(s) and ${reviewCount} question(s) marked for review.`;
                } else if (unansweredCount > 0) {
                    warningBox.style.display = 'block';
                    warningText.textContent = `You have ${unansweredCount} unanswered question(s). You can return to complete them.`;
                } else if (reviewCount > 0) {
                    warningBox.style.display = 'block';
                    warningText.textContent = `You have ${reviewCount} question(s) marked for review.`;
                } else {
                    warningBox.style.display = 'none';
                }
            }

            submitModal.classList.add('is-open');
        }

        if (btnHeaderSubmit) btnHeaderSubmit.addEventListener('click', openSubmitModal);
        if (btnBottomSubmit) btnBottomSubmit.addEventListener('click', openSubmitModal);

        if (btnModalCancel) {
            btnModalCancel.addEventListener('click', () => {
                submitModal.classList.remove('is-open');
            });
        }

        if (btnModalConfirm) {
            btnModalConfirm.addEventListener('click', () => {
                btnModalConfirm.disabled = true;
                btnModalConfirm.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
                isAutoSubmitting = true;
                examForm.submit();
            });
        }

        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && submitModal && submitModal.classList.contains('is-open')) {
                submitModal.classList.remove('is-open');
            }
        });
    }

    // -------------------------------------------------------------
    // 4. Generic Table Quick-Filter
    // -------------------------------------------------------------
    const searchInputs = document.querySelectorAll('[data-table-search]');
    searchInputs.forEach((input) => {
        input.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            const targetTable = document.querySelector(input.getAttribute('data-table-search'));
            if (targetTable) {
                const rows = targetTable.querySelectorAll('tbody tr');
                rows.forEach((row) => {
                    const rowText = row.textContent.toLowerCase();
                    row.style.display = rowText.includes(term) ? '' : 'none';
                });
            }
        });
    });

    // -------------------------------------------------------------
    // 5. Mobile Sidebar Navigation Drawer & Backdrop
    // -------------------------------------------------------------
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');

    if (mobileMenuToggle && sidebar) {
        mobileMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('mobile-open');
            if (sidebarBackdrop) {
                sidebarBackdrop.classList.toggle('active');
            }
        });

        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener('click', () => {
                sidebar.classList.remove('mobile-open');
                sidebarBackdrop.classList.remove('active');
            });
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
                sidebar.classList.remove('mobile-open');
                if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
            }
        });
    }

    // -------------------------------------------------------------
    // 6. Smooth Dashboard Counter Roll-Up Animation
    // -------------------------------------------------------------
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReducedMotion) {
        const counterElements = document.querySelectorAll('[data-counter]');
        counterElements.forEach((el) => {
            const rawTarget = el.getAttribute('data-counter');
            const targetVal = parseFloat(rawTarget);
            if (isNaN(targetVal)) return;

            const suffix = el.getAttribute('data-counter-suffix') || '';
            const prefix = el.getAttribute('data-counter-prefix') || '';
            const isFloat = rawTarget.includes('.');
            const duration = 800; // ms
            const startTime = performance.now();

            function step(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                // easeOutQuad
                const easeProgress = progress * (2 - progress);
                const currentVal = targetVal * easeProgress;

                if (isFloat) {
                    el.textContent = `${prefix}${currentVal.toFixed(1)}${suffix}`;
                } else {
                    el.textContent = `${prefix}${Math.round(currentVal)}${suffix}`;
                }

                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    el.textContent = `${prefix}${isFloat ? targetVal.toFixed(1) : targetVal}${suffix}`;
                }
            }

            requestAnimationFrame(step);
        });
    }

});
