import { useState } from 'react';
import { Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentChatPanel } from './AgentChatPanel';

export const AgentChatButton = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {!isOpen && (
        <Button
          onClick={() => setIsOpen(true)}
          size="lg"
          className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-all z-40"
        >
          <Bot className="h-6 w-6" />
        </Button>
      )}
      <AgentChatPanel isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  );
};

// Made with Bob
