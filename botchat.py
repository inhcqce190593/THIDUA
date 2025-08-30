import React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Mic, Waves } from "lucide-react";

const ChatFPTU = () => {
  return (
    <div className="min-h-screen bg-[#121212] text-white flex flex-col items-center p-8">
      <h1 className="text-4xl font-bold mb-2">ChatFPTU</h1>
      <p className="text-sm text-gray-400 mb-8 text-center">
        Chatbot tư vấn sinh viên về các quy trình đào tạo và thủ tục hành chính<br />
        tại trường Đại học FPT Cần Thơ
      </p>

      <div className="flex flex-wrap gap-4 justify-center mb-8">
        <Button variant="outline" className="bg-[#1f1f1f] border-none hover:bg-[#2c2c2c]">
          Cách đóng học phí?
        </Button>
        <Button variant="outline" className="bg-[#1f1f1f] border-none hover:bg-[#2c2c2c]">
          Em muốn bảo lưu 1 năm để năm sau học lại được không?
        </Button>
        <Button variant="outline" className="bg-[#1f1f1f] border-none hover:bg-[#2c2c2c]">
          Em muốn chuyển ngành
        </Button>
        <Button variant="outline" className="bg-[#1f1f1f] border-none hover:bg-[#2c2c2c]">
          Em bị mất thẻ sinh viên thì làm sao?
        </Button>
      </div>

      <div className="w-full max-w-2xl flex items-center bg-[#1e1e1e] rounded-full px-4 py-2">
        <Input
          placeholder="Hỏi bất kỳ điều gì"
          className="bg-transparent border-none text-white focus:outline-none flex-1"
        />
        <Button size="icon" variant="ghost" className="text-white">
          <Mic className="w-5 h-5" />
        </Button>
        <Button size="icon" className="bg-white text-black ml-2">
          <Waves className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
};

export default ChatFPTU;
