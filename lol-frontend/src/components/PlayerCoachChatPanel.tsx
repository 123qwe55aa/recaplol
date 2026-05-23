import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCoachChat } from '../hooks/useCoach';
import type { CoachChatResponse } from '../types';

interface PlayerCoachChatPanelProps {
  puuid: string;
}

interface ChatMessage {
  role: 'user' | 'coach';
  text: string;
}

export function PlayerCoachChatPanel({ puuid }: PlayerCoachChatPanelProps) {
  const chat = useCoachChat(puuid);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || chat.isPending) return;

    setQuestion('');
    setMessages((current) => [...current, { role: 'user', text: trimmed }]);
    try {
      const answer: CoachChatResponse = await chat.mutateAsync(trimmed);
      setMessages((current) => [...current, { role: 'coach', text: answer.answer }]);
    } catch {
      // The mutation exposes the error state below; keep the user's question visible.
    }
  };

  return (
    <section className="rounded-lg border border-gray-800 bg-gray-900 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">问 AI Coach</h3>
          <p className="mt-1 text-sm text-gray-400">
            基于已生成的训练报告追问具体练习方向。
          </p>
        </div>
        <Link
          to={`/coach/${puuid}`}
          className="inline-flex shrink-0 items-center justify-center rounded-lg bg-gray-800 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
        >
          打开完整 AI 教练
        </Link>
      </div>

      <div className="mt-4 space-y-3">
        {messages.length === 0 && (
          <p className="rounded-lg bg-gray-800 px-4 py-3 text-sm text-gray-300">
            可以问：我下一局最该注意什么？如果还没有报告，先打开完整 AI 教练生成一份。
          </p>
        )}
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={message.role === 'user' ? 'text-right' : 'text-left'}
          >
            <p
              className={`inline-block max-w-3xl rounded-lg px-4 py-3 text-sm leading-6 ${
                message.role === 'user'
                  ? 'bg-yellow-500 text-black'
                  : 'bg-gray-700 text-gray-100'
              }`}
            >
              {message.text}
            </p>
          </div>
        ))}
        {chat.isPending && (
          <p className="inline-block rounded-lg bg-gray-800 px-4 py-3 text-sm text-gray-300">
            AI 正在思考...
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 md:flex-row">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="问 AI Coach 一个问题..."
          className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white placeholder-gray-500 focus:border-yellow-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!question.trim() || chat.isPending}
          className="rounded-lg bg-yellow-500 px-5 py-3 font-bold text-black transition-colors hover:bg-yellow-400 disabled:opacity-50"
        >
          发送
        </button>
      </form>

      {chat.error && (
        <p className="mt-3 text-sm text-red-400">
          追问失败。请先确认完整 AI 教练页面已有训练报告，或稍后再试。
        </p>
      )}
    </section>
  );
}
