import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RuneSimulator } from '../RuneSimulator';

describe('RuneSimulator', () => {
  it('supports collapsing and expanding', () => {
    render(<RuneSimulator recommendedRunes={[]} defaultCollapsed />);
    expect(screen.queryByText('当前符文页')).toBeNull();

    const toggle = screen.getByRole('button', { name: 'toggle-rune-simulator' });
    fireEvent.click(toggle);
    expect(screen.getByText('当前符文页')).toBeInTheDocument();

    fireEvent.click(toggle);
    expect(screen.queryByText('当前符文页')).toBeNull();
  });

  it('keeps secondary path different from primary path', () => {
    render(<RuneSimulator recommendedRunes={['奥术彗星']} />);

    const primarySelect = screen.getByLabelText('primary-path') as HTMLSelectElement;
    const secondarySelect = screen.getByLabelText('secondary-path') as HTMLSelectElement;

    expect(primarySelect.value).toBe('precision');
    expect(secondarySelect.value).toBe('domination');

    fireEvent.change(primarySelect, { target: { value: 'domination' } });

    expect(primarySelect.value).toBe('domination');
    expect(secondarySelect.value).not.toBe('domination');
  });

  it('updates summary after selecting runes and shards', () => {
    render(<RuneSimulator recommendedRunes={[]} />);

    fireEvent.click(screen.getByRole('button', { name: '征服者' }));
    fireEvent.click(screen.getByRole('button', { name: '气定神闲' }));
    fireEvent.click(screen.getAllByRole('button', { name: '自适应之力' })[0]);

    const summary = screen.getByText('当前符文页').parentElement;
    expect(summary).not.toBeNull();
    expect(summary).toHaveTextContent('征服者 / 气定神闲');
    expect(summary).toHaveTextContent('碎片：自适应之力');
  });

  it('saves preset to localStorage', () => {
    const storage = new Map<string, string>();
    Object.defineProperty(globalThis, 'localStorage', {
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
      },
      configurable: true,
    });

    render(<RuneSimulator recommendedRunes={[]} />);
    fireEvent.change(screen.getByPlaceholderText('预设名称'), { target: { value: '我的精密页' } });
    fireEvent.click(screen.getByRole('button', { name: '征服者' }));
    fireEvent.click(screen.getByRole('button', { name: '保存本地预设' }));

    const saved = storage.get('lol_rune_simulator_presets_v2');
    expect(saved).toBeTruthy();
    expect(saved ?? '').toContain('"primaryPathId":"precision"');
    expect(saved ?? '').toContain('"name":"我的精密页"');
    expect(screen.getByText('已保存预设')).toBeInTheDocument();
  });

  it('loads and deletes selected preset', () => {
    const storage = new Map<string, string>();
    Object.defineProperty(globalThis, 'localStorage', {
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
      },
      configurable: true,
    });

    render(<RuneSimulator recommendedRunes={[]} />);

    fireEvent.change(screen.getByPlaceholderText('预设名称'), { target: { value: 'P1' } });
    fireEvent.click(screen.getByRole('button', { name: '征服者' }));
    fireEvent.click(screen.getByRole('button', { name: '保存本地预设' }));

    fireEvent.change(screen.getByPlaceholderText('预设名称'), { target: { value: 'P2' } });
    fireEvent.click(screen.getByRole('button', { name: '强攻' }));
    fireEvent.click(screen.getByRole('button', { name: '保存本地预设' }));

    const presetSelect = screen.getByLabelText('preset-select') as HTMLSelectElement;
    const p1Option = Array.from(presetSelect.options).find((option) => option.textContent === 'P1');
    expect(p1Option).toBeTruthy();
    fireEvent.change(presetSelect, { target: { value: p1Option?.value } });
    fireEvent.click(screen.getByRole('button', { name: '读取预设' }));

    const summary = screen.getByText('当前符文页').parentElement;
    expect(summary).toHaveTextContent('征服者');

    fireEvent.click(screen.getByRole('button', { name: '删除预设' }));
    expect(screen.getByText('已删除预设')).toBeInTheDocument();
  });

  it('copies summary to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    render(<RuneSimulator recommendedRunes={[]} />);
    fireEvent.click(screen.getByRole('button', { name: '复制当前符文页' }));

    await Promise.resolve();
    expect(writeText).toHaveBeenCalledTimes(1);
  });

  it('fetches rune info update and shows description', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ['99.1.1'],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ([
          {
            slots: [
              {
                runes: [
                  {
                    name: '征服者',
                    icon: 'perk-images/Styles/Precision/Conqueror/Conqueror.png',
                    shortDesc: '<b>测试描述</b>',
                    longDesc: '<i>长描述</i>',
                  },
                ],
              },
            ],
          },
        ]),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ([]),
      });

    vi.stubGlobal('fetch', fetchMock);

    render(<RuneSimulator recommendedRunes={[]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Fetch 符文更新' }));

    await screen.findByText('已更新符文信息（99.1.1）');
    fireEvent.click(screen.getByRole('button', { name: '征服者' }));
    expect(screen.getByText('符文信息')).toBeInTheDocument();
    expect(screen.getByText('测试描述')).toBeInTheDocument();
    expect(screen.getByText('来源版本: 99.1.1')).toBeInTheDocument();
  });
});
