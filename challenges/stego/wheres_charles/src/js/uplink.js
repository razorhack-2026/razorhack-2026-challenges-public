(async () => {
  try {
    const response = await fetch('/api/session.php', { cache: 'no-store', credentials: 'same-origin' });
    if (response.status === 401) {
      window.location.replace('/');
      return;
    }
    if (!response.ok) throw new Error(`Session check failed (${response.status}).`);
    const session = await response.json();
    if (!session.authenticated) {
      window.location.replace('/');
      return;
    }
    document.querySelectorAll('[data-operator]').forEach((element) => {
      element.textContent = session.crew_id;
    });
    document.documentElement.classList.remove('auth-pending');
    loadEarnedFlags();
  } catch (error) {
    document.documentElement.classList.remove('auth-pending');
    const notice = document.createElement('div');
    notice.className = 'auth-error';
    notice.textContent = `Unable to verify your session: ${error.message}`;
    document.body.prepend(notice);
    return;
  }

  
  const postJson = async (url, payload) => {
      const response = await fetch(url, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify(payload),
      });

      const raw = await response.text();

      let data;

      try {
          data = JSON.parse(raw);
      } catch (error) {
          console.error('Invalid server response:', {
              status: response.status,
              contentType: response.headers.get('content-type'),
              body: raw
          });

          throw new Error(
              `Server returned invalid JSON (${response.status}). Check console for details.`
          );
      }

      if (!response.ok && !data.error) {
          throw new Error(`Request failed (${response.status}).`);
      }

      return data;
  };


  const renderChallengeState = (state) => {
    const progress = document.querySelector('[data-challenge-progress]');
    if (progress) progress.textContent = `${state.completed} / ${state.total}`;
    return state;
  };

  const getChallengeState = async () => {
    const response = await fetch('/api/challenge-state.php', {
      cache: 'no-store',
      credentials: 'same-origin',
    });
    if (!response.ok) throw new Error(`Challenge status request failed (${response.status}).`);
    return renderChallengeState(await response.json());
  };

  try {
    await getChallengeState();
  } catch (error) {
    const progress = document.querySelector('[data-challenge-progress]');
    if (progress) progress.textContent = `STATUS ERROR // ${error.message}`;
  }

  const ladderCanvas = document.querySelector('[data-ladder-canvas]');
  if (ladderCanvas) {
    const rungModels = [];
    const rungCount = document.querySelector('[data-rung-count]');
    const message = document.querySelector('[data-ladder-message]');
    const result = document.querySelector('[data-ladder-result]');
    let nextRungId = 1;

    // Layout constants (px). Keep in sync with uplink-parallel.css.
    const COMPONENT_W = 96;      // width of one component cell
    const MIN_BRANCH_COL_W = 128; // minimum column width when a parallel path hangs under it
    const BRANCH_TOP = 72;       // distance from top of a column to the first parallel path
    const BRANCH_H = 100;        // height of one parallel path row
    const WIRE_Y = 13.5;         // y of the wire inside a component row

    const makeElement = (tag, className, text) => {
      const element = document.createElement(tag);
      if (className) element.className = className;
      if (text !== undefined) element.textContent = text;
      return element;
    };

    const updateRungCount = () => {
      rungCount.textContent = `${rungModels.length} RUNG${rungModels.length === 1 ? '' : 'S'}`;
    };

    const addComponent = (path, kind, mode) => {
      if (kind === 'coil' && path.some((component) => component.kind === 'coil')) return;
      const component = { kind, mode, tag: '' };
      const coilIndex = path.findIndex((item) => item.kind === 'coil');
      if (kind === 'contact' && coilIndex >= 0) path.splice(coilIndex, 0, component);
      else path.push(component);
      renderLadder();
    };

    // `model` is passed only for components on the main rung; those can have
    // parallel paths hanging under them.
    const renderComponent = (component, path, model) => {
      const block = makeElement('div', `ladder-component ${component.kind}-block`);
      const symbol = makeElement('span', 'ladder-symbol');
      if (component.kind === 'contact') {
        symbol.classList.add('contact-symbol');
        symbol.dataset.contactType = component.mode;
        symbol.append(makeElement('span', 'contact-bracket', '['));
        symbol.append(makeElement('span', 'contact-diagonal'));
        symbol.append(makeElement('span', 'contact-bracket', ']'));
      } else {
        symbol.classList.add('coil-symbol');
        symbol.append(makeElement('span', 'coil-paren', '('));
        symbol.append(makeElement('span', 'coil-paren', ')'));
      }
      block.append(symbol);

      const tag = makeElement('input', 'component-tag');
      tag.type = 'text';
      tag.value = component.tag;
      tag.placeholder = component.kind === 'contact' ? 'CONTACT TAG' : 'COIL TAG';
      tag.setAttribute('aria-label', `${component.kind} tag`);
      tag.autocomplete = 'off';
      tag.spellcheck = false;
      tag.addEventListener('input', () => { component.tag = tag.value.trim().toUpperCase(); });
      block.append(tag);

      const type = document.createElement('select');
      type.className = 'component-type';
      type.setAttribute('aria-label', `${component.kind} type`);
      const options = component.kind === 'contact'
        ? [['NO', 'NO'], ['NC', 'NC']]
        : [['OTE', 'OTE'], ['OTL', 'OTL'], ['OTU', 'OTU']];
      options.forEach(([value, label]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        type.append(option);
      });
      type.value = component.mode;
      type.addEventListener('change', () => {
        component.mode = type.value;
        renderLadder();
      });
      block.append(type);

      const remove = makeElement('button', 'component-remove', '×');
      remove.type = 'button';
      remove.setAttribute('aria-label', 'REMOVE COMPONENT');
      remove.addEventListener('click', () => {
        path.splice(path.indexOf(component), 1);
        // Parallel paths hang off this component, so they go with it.
        if (model) model.branches = model.branches.filter((branch) => branch.anchor !== component);
        renderLadder();
      });
      block.append(remove);

      if (model) {
        const parallel = makeElement('button', 'component-branch', '∥');
        parallel.type = 'button';
        parallel.title = 'ADD PARALLEL PATH UNDER THIS COMPONENT';
        parallel.setAttribute('aria-label', 'ADD PARALLEL PATH UNDER THIS COMPONENT');
        parallel.addEventListener('click', () => {
          model.branches.push({ anchor: component, components: [] });
          renderLadder();
        });
        block.append(parallel);
      }
      return block;
    };

    // Left/right piece of main wire between a power rail and the first/last
    // component. Parallel paths under the first/last component tie into the
    // rail through here, instead of drawing their own vertical leg.
    const renderStub = (branchList) => {
      const stub = makeElement('div', 'rung-stub');
      stub.append(makeElement('span', 'rung-stub-wire'));
      branchList.forEach((_, slot) => {
        const link = makeElement('span', 'rung-stub-wire rung-stub-branch');
        link.style.top = `${BRANCH_TOP + slot * BRANCH_H + WIRE_Y}px`;
        stub.append(link);
      });
      return stub;
    };

    const renderBranch = (model, branch, slot, isFirst, isLast) => {
      const row = makeElement('div', 'branch-row');
      const rowTop = BRANCH_TOP + slot * BRANCH_H;
      row.style.top = `${rowTop}px`;
      row.style.setProperty('--row-top', `${rowTop}px`);

      // Vertical legs make the U. Skipped on a side that meets a power rail.
      if (!isFirst) row.append(makeElement('span', 'branch-leg branch-leg-left'));
      if (!isLast) row.append(makeElement('span', 'branch-leg branch-leg-right'));

      const path = makeElement('div', 'branch-path');
      if (branch.components.length) {
        branch.components.forEach((component) => {
          path.append(renderComponent(component, branch.components, null));
        });
      } else {
        const empty = makeElement('div', 'branch-empty');
        empty.append(makeElement('span', 'branch-empty-label', 'EMPTY PATH'));
        path.append(empty);
      }
      row.append(path);

      const tools = makeElement('div', 'branch-tools');
      const addTool = (label, action, className = '') => {
        const button = makeElement('button', `rung-tool ${className}`.trim(), label);
        button.type = 'button';
        button.addEventListener('click', action);
        tools.append(button);
      };
      addTool('+NO', () => addComponent(branch.components, 'contact', 'NO'));
      addTool('+NC', () => addComponent(branch.components, 'contact', 'NC'));
      // A path under a coil is a parallel output, so it may hold a coil too.
      if (branch.anchor.kind === 'coil') {
        addTool('+COIL', () => addComponent(branch.components, 'coil', 'OTE'));
      }
      addTool('×', () => {
        model.branches.splice(model.branches.indexOf(branch), 1);
        renderLadder();
      }, 'rung-delete');
      row.append(tools);
      return row;
    };

    const renderRungTrack = (model) => {
      const track = makeElement('div', 'rung-track');
      const byAnchor = new Map(model.components.map((component) => [component, []]));
      model.branches.forEach((branch) => {
        if (byAnchor.has(branch.anchor)) byAnchor.get(branch.anchor).push(branch);
      });
      const lastIndex = model.components.length - 1;
      const branchesAt = (index) => (model.components[index] ? byAnchor.get(model.components[index]) : []);

      track.append(renderStub(branchesAt(0)));

      const components = makeElement('div', 'ladder-components');
      model.components.forEach((component, index) => {
        const list = byAnchor.get(component);
        const column = makeElement('div', 'rung-col');
        column.append(renderComponent(component, model.components, model));
        if (list.length) {
          const longest = Math.max(...list.map((branch) => branch.components.length));
          column.style.minWidth = `${Math.max(longest * COMPONENT_W, MIN_BRANCH_COL_W)}px`;
          column.style.height = `${BRANCH_TOP + list.length * BRANCH_H}px`;
          list.forEach((branch, slot) => {
            column.append(renderBranch(model, branch, slot, index === 0, index === lastIndex));
          });
        }
        components.append(column);
      });
      if (!model.components.length) {
        components.append(makeElement('span', 'rung-placeholder', 'ADD A CONTACT OR COIL'));
      }
      track.append(components);

      track.append(renderStub(branchesAt(lastIndex)));
      return track;
    };

    const renderRung = (model, index) => {
      const row = makeElement('section', 'ladder-rung');
      const heading = makeElement('div', 'rung-heading');
      heading.append(makeElement('span', '', `RUNG ${String(index + 1).padStart(2, '0')}`));
      const tools = makeElement('div', 'rung-tools');
      [
        ['+ NO CONTACT', () => addComponent(model.components, 'contact', 'NO')],
        ['+ NC CONTACT', () => addComponent(model.components, 'contact', 'NC')],
        ['+ COIL', () => addComponent(model.components, 'coil', 'OTE')],
      ].forEach(([label, action]) => {
        const button = makeElement('button', 'rung-tool', label);
        button.type = 'button';
        button.addEventListener('click', action);
        tools.append(button);
      });

      const remove = makeElement('button', 'rung-tool rung-delete', '× DELETE RUNG');
      remove.type = 'button';
      remove.addEventListener('click', () => {
        rungModels.splice(rungModels.indexOf(model), 1);
        renderLadder();
      });
      tools.append(remove);
      heading.append(tools);
      row.append(heading);

      row.append(renderRungTrack(model));
      return row;
    };

    function renderLadder() {
      ladderCanvas.replaceChildren();
      if (!rungModels.length) {
        ladderCanvas.append(makeElement('div', 'ladder-empty', 'NO RUNGS IN PROGRAM'));
      } else {
        rungModels.forEach((model, index) => ladderCanvas.append(renderRung(model, index)));
      }
      updateRungCount();
    }

    document.querySelector('[data-add-rung]').addEventListener('click', () => {
      rungModels.push({ id: nextRungId++, components: [], branches: [] });
      message.textContent = '';
      message.className = 'form-message';
      renderLadder();
    });

    document.querySelector('[data-compile]').addEventListener('click', async (event) => {
      const button = event.currentTarget;
      const rungs = rungModels.map((rung) => ({
        components: rung.components.map(({ kind, mode, tag }) => ({ kind, mode, tag })),
        branches: rung.branches.map((branch) => ({
          // Index of the main-rung component this path sits under.
          anchor: rung.components.indexOf(branch.anchor),
          components: branch.components.map(({ kind, mode, tag }) => ({ kind, mode, tag })),
        })),
      }));
      message.className = 'form-message';
      message.textContent = 'COMPILING PROGRAM...';
      button.disabled = true;
      result.classList.remove('show');
      try {
        const data = await postJson('/api/validate-ladder.php', { rungs });
        if (!data.success) throw new Error(data.error || 'PROGRAM COULD NOT BE COMPILED.');
        message.textContent = data.message;
        message.className = 'form-message success';
        result.replaceChildren();
        result.append(makeElement('div', 'notice success', data.message));
        const flag = makeElement('p');
        flag.append(document.createTextNode('FLAG: '), makeElement('code', '', data.flag));
        const cameras = makeElement('a', 'button', 'CARGO BAY VIEW');
        cameras.href = '/cameras.html';
        result.append(flag, cameras);
        result.classList.add('show');
        await getChallengeState();
      } catch (error) {
        message.textContent = error.message;
        message.className = 'form-message error';
      } finally {
        button.disabled = false;
      }
    });

    renderLadder();
  }

  const cameraVideo = document.querySelector('[data-camera-video]');
  if (cameraVideo) {
    const placeholder = document.querySelector('[data-video-placeholder]');
    const overlay = document.querySelector('[data-camera-overlay]');
    const refreshCamera = async () => {
      try {
        const state = await getChallengeState();
        if (!state.video) {
          cameraVideo.pause();
          cameraVideo.removeAttribute('src');
          cameraVideo.load();
          cameraVideo.classList.add('hidden');
          placeholder.classList.remove('hidden');
          overlay.textContent = 'OFFLINE';
          return;
        }
        const source = `/api/media.php?file=${encodeURIComponent(state.video)}`;
        if (cameraVideo.dataset.source !== source) {
          cameraVideo.dataset.source = source;
          cameraVideo.src = source;
          cameraVideo.load();
        }
        cameraVideo.classList.remove('hidden');
        placeholder.classList.add('hidden');
        overlay.textContent = 'CAM-01 // LIVE FEED';
        cameraVideo.play().catch((error) => {
          overlay.textContent = `PLAYBACK ERROR // ${error.message}`;
        });
      } catch (error) {
        overlay.textContent = `FEED ERROR // ${error.message}`;
      }
    };
    refreshCamera();
    window.setInterval(refreshCamera, 5000);
  }
  
  const filesList = document.querySelector('[data-files-list]');
  if (filesList) {
    const fileStatus = document.querySelector('[data-files-status]');
    const renderFiles = async () => {
      try {
        const response = await fetch('/api/files.php', {
          cache: 'no-store',
          credentials: 'same-origin',
        });
        if (!response.ok) throw new Error(`DIRECTORY REQUEST FAILED (${response.status}).`);
        const data = await response.json();
        filesList.replaceChildren();
        data.files.forEach((file) => {
          const link = document.createElement('a');
          link.className = 'asset-row file-link';
          link.href = file.download;
          link.setAttribute('download', file.name);
          link.textContent = file.name;
          filesList.append(link);
        });
        fileStatus.textContent = `${data.files.length} ITEMS`;
      } catch (error) {
        fileStatus.textContent = `DIRECTORY ERROR // ${error.message}`;
      }
    };
    renderFiles();
  }

  async function loadEarnedFlags() {
    const container = document.querySelector('[data-earned-flags]');

    if (!container) return;

    try {
        const response = await fetch('/api/get-flags.php', {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to retrieve flags.');
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error('Flag retrieval unsuccessful.');
        }

        container.replaceChildren();

        if (!data.earnedFlags || data.earnedFlags.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'hidden-hint';
            empty.textContent = 'NO RECOVERED FLAGS';
            container.appendChild(empty);
            return;
        }

        data.earnedFlags.forEach(item => {
            const entry = document.createElement('div');
            entry.className = 'earned-flag-entry';

            const name = document.createElement('span');
            name.className = 'earned-flag-name';
            name.textContent = item.challenge.toUpperCase();

            const flag = document.createElement('code');
            flag.className = 'earned-flag-value';
            flag.textContent = item.flag;

            const copy = document.createElement('button');
            copy.type = 'button';
            copy.className = 'button';
            copy.textContent = 'COPY';

            copy.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(item.flag);
                    copy.textContent = 'COPIED';

                    setTimeout(() => {
                        copy.textContent = 'COPY';
                    }, 1500);
                } catch {
                    copy.textContent = 'COPY FAILED';
                }
            });

            entry.append(name, flag, copy);
            container.appendChild(entry);
        });

    } catch (error) {
        console.error('Error loading recovered flags:', error);
        container.textContent = 'UNABLE TO LOAD RECOVERED FLAGS';
    }
}
document.addEventListener('DOMContentLoaded', loadEarnedFlags);
})();